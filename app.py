import os
import time
import hashlib
import requests
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from urllib.parse import urlencode
from functools import wraps
from token_store import TokenStore
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
token_store = TokenStore()
load_dotenv()

# Configuration
API_KEY = os.environ.get('LASTFM_API_KEY', 'your_api_key_here')
API_SECRET = os.environ.get('LASTFM_API_SECRET', 'your_api_secret_here')
BASE_URL = 'https://ws.audioscrobbler.com/2.0/'
AUTH_URL = 'http://www.last.fm/api/auth'

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW = 60  # seconds

class LastFMError(Exception):
    """Custom exception for Last.fm API errors"""
    pass

class RateLimiter:
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key, limit=RATE_LIMIT_REQUESTS, window=RATE_LIMIT_WINDOW):
        now = datetime.now()
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests
        self.requests[key] = [req_time for req_time in self.requests[key] 
                             if now - req_time < timedelta(seconds=window)]
        
        if len(self.requests[key]) >= limit:
            return False
        
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter()

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'oauth_token' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(f):
    """Decorator for rate limiting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if not rate_limiter.is_allowed(client_ip):
            return jsonify({'success': False, 'error': 'Rate limit exceeded'}), 429
        return f(*args, **kwargs)
    return decorated_function

def validate_input(data, required_fields):
    """Validate input data"""
    errors = []
    for field in required_fields:
        if field not in data or not data[field].strip():
            errors.append(f'{field} is required')
    return errors

def get_auth_url():
    """Generate Last.fm authentication URL"""
    try:
        callback_url = url_for('callback', _external=True)
        params = {
            'api_key': API_KEY,
            'cb': callback_url
        }
        return f"{AUTH_URL}?{urlencode(params)}"
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}")
        raise LastFMError("Failed to generate authentication URL")

def get_api_signature(params):
    """Generate API signature for Last.fm requests"""
    try:
        # Sort parameters and concatenate them
        string_to_sign = ''.join([f"{k}{params[k]}" for k in sorted(params.keys())])
        string_to_sign += API_SECRET
        # Calculate md5 hash - Last.fm API requires MD5, using usedforsecurity=False
        # as this is not for security purposes but for API signature matching
        return hashlib.md5(string_to_sign.encode('utf-8'), usedforsecurity=False).hexdigest()  # nosec B324
    except Exception as e:
        logger.error(f"Error generating API signature: {e}")
        raise LastFMError("Failed to generate API signature")

def make_lastfm_request(params, method='GET'):
    """Make authenticated request to Last.fm API"""
    try:
        params['format'] = 'json'
        
        if method == 'POST':
            response = requests.post(BASE_URL, data=params, timeout=10)
        else:
            response = requests.get(BASE_URL, params=params, timeout=10)
        
        response.raise_for_status()
        data = response.json()
        
        if 'error' in data:
            error_msg = data.get('message', f"Last.fm API error: {data['error']}")
            logger.error(f"Last.fm API error: {error_msg}")
            raise LastFMError(error_msg)
        
        return data
    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        raise LastFMError("Failed to connect to Last.fm")
    except ValueError as e:
        logger.error(f"JSON decode error: {e}")
        raise LastFMError("Invalid response from Last.fm")

@app.errorhandler(LastFMError)
def handle_lastfm_error(error):
    return jsonify({'success': False, 'error': str(error)}), 400

@app.errorhandler(429)
def handle_rate_limit(error):
    return jsonify({'success': False, 'error': 'Rate limit exceeded. Please try again later.'}), 429

@app.route('/callback')
def callback():
    """Handle Last.fm authentication callback"""
    token = request.args.get('token')
    if not token:
        flash('Authentication failed: No token received', 'error')
        return redirect(url_for('home'))

    try:
        # Get session key
        params = {
            'api_key': API_KEY,
            'method': 'auth.getSession',
            'token': token,
        }
        params['api_sig'] = get_api_signature(params)
        
        data = make_lastfm_request(params)

        if 'session' in data:
            session['oauth_token'] = data['session']['key']
            session['user_name'] = data['session']['name']
            session['last_user'] = data['session']['name']
            
            # Save token to persistent storage
            token_store.save_token(data['session']['name'], data['session']['key'])
            flash(f'Successfully authenticated as {data["session"]["name"]}', 'success')
            return redirect(url_for('home'))
        
    except LastFMError as e:
        flash(f'Authentication failed: {str(e)}', 'error')
    except Exception as e:
        logger.error(f"Unexpected error in callback: {e}")
        flash('Authentication failed: Unexpected error', 'error')
    
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    """Handle user logout"""
    if 'user_name' in session:
        token_store.delete_token(session['user_name'])
        flash('Successfully logged out', 'info')
    session.clear()
    return redirect(url_for('home'))

@app.route('/')
def home():
    """Main home page"""
    # Check for stored authentication
    if 'oauth_token' not in session and 'user_name' not in session:
        stored_token = None
        if 'last_user' in session:
            stored_token = token_store.get_token(session['last_user'])
        
        if stored_token:
            session['oauth_token'] = stored_token
            session['user_name'] = session['last_user']
        else:
            try:
                auth_url = get_auth_url()
                return render_template('index.html', auth_url=auth_url)
            except LastFMError as e:
                flash(f'Error: {str(e)}', 'error')
                return render_template('index.html')

    # Get user's recent tracks
    try:
        recent_tracks = get_user_recent_tracks()
        return render_template('index.html', 
                             recent_tracks=recent_tracks,
                             user_name=session.get('user_name'))
    except LastFMError as e:
        flash(f'Error loading recent tracks: {str(e)}', 'error')
        return render_template('index.html', 
                             user_name=session.get('user_name'))

def get_user_recent_tracks(limit=10):
    """Get user's recent tracks from Last.fm"""
    if 'oauth_token' not in session or 'user_name' not in session:
        return []

    try:
        params = {
            'method': 'user.getRecentTracks',
            'user': session.get('user_name'),
            'api_key': API_KEY,
            'limit': min(limit, 50)  # Limit to prevent abuse
        }

        data = make_lastfm_request(params)
        
        if 'recenttracks' in data and 'track' in data['recenttracks']:
            tracks = data['recenttracks']['track']
            # Ensure tracks is always a list
            if isinstance(tracks, dict):
                tracks = [tracks]
            return tracks
        
        return []
    except LastFMError:
        raise
    except Exception as e:
        logger.error(f"Error getting recent tracks: {e}")
        raise LastFMError("Failed to load recent tracks")

@app.route('/now-playing-info')
@require_auth
@rate_limit
def get_now_playing_info():
    """Get current now playing track"""
    try:
        params = {
            'method': 'user.getRecentTracks',
            'user': session.get('user_name'),
            'api_key': API_KEY,
            'limit': 1
        }

        data = make_lastfm_request(params)
        
        if 'recenttracks' in data and 'track' in data['recenttracks']:
            tracks = data['recenttracks']['track']
            if isinstance(tracks, dict):
                tracks = [tracks]
            
            if tracks and tracks[0].get('@attr', {}).get('nowplaying'):
                track = tracks[0]
                return jsonify({
                    'success': True,
                    'nowplaying': True,
                    'track': {
                        'name': track.get('name', ''),
                        'artist': track.get('artist', {}).get('#text', ''),
                        'album': track.get('album', {}).get('#text', ''),
                        'image': track.get('image', [{}])[-1].get('#text', ''),
                        'url': track.get('url', '')
                    }
                })
        
        return jsonify({'success': True, 'nowplaying': False})
        
    except LastFMError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting now playing: {e}")
        return jsonify({'success': False, 'error': 'Failed to get now playing'}), 500

@app.route('/scrobble', methods=['POST'])
@require_auth
@rate_limit
def scrobble():
    """Scrobble a track to Last.fm with custom timestamp"""
    try:
        # Validate input
        errors = validate_input(request.form, ['artist', 'track'])
        if errors:
            return jsonify({'success': False, 'errors': errors}), 400

        artist = request.form['artist'].strip()
        track = request.form['track'].strip()
        album = request.form.get('album', '').strip()
        
        # Custom timestamp handling
        custom_time = request.form.get('scrobble_time', '').strip()
        timestamp = int(time.time())  # Default to now
        
        if custom_time:
            try:
                # Parse various time formats
                if custom_time.lower() == 'now':
                    timestamp = int(time.time())
                elif custom_time.isdigit():
                    # Minutes ago
                    minutes_ago = int(custom_time)
                    if minutes_ago > 14 * 24 * 60:  # Last.fm limit: 14 days
                        return jsonify({'success': False, 'error': 'Cannot scrobble tracks older than 14 days'}), 400
                    timestamp = int(time.time()) - (minutes_ago * 60)
                else:
                    # Try to parse as datetime
                    try:
                        from dateutil import parser
                        dt = parser.parse(custom_time)
                        timestamp = int(dt.timestamp())
                        
                        # Check Last.fm limits
                        now = int(time.time())
                        if timestamp > now:
                            return jsonify({'success': False, 'error': 'Cannot scrobble tracks in the future'}), 400
                        if now - timestamp > 14 * 24 * 60 * 60:  # 14 days
                            return jsonify({'success': False, 'error': 'Cannot scrobble tracks older than 14 days'}), 400
                    except ImportError:
                        return jsonify({'success': False, 'error': 'Invalid time format'}), 400
                        
            except (ValueError, TypeError) as e:
                return jsonify({'success': False, 'error': 'Invalid time format'}), 400
        
        # Additional validation
        if len(artist) > 200 or len(track) > 200:
            return jsonify({'success': False, 'error': 'Artist or track name too long'}), 400

        params = {
            'method': 'track.scrobble',
            'api_key': API_KEY,
            'sk': session['oauth_token'],
            'artist': artist,
            'track': track,
            'timestamp': timestamp
        }
        
        if album:
            params['album'] = album
        
        params['api_sig'] = get_api_signature(params)
        
        data = make_lastfm_request(params, method='POST')
        
        logger.info(f"Scrobbled: {artist} - {track} at {datetime.fromtimestamp(timestamp)} for user {session.get('user_name')}")
        return jsonify({'success': True, 'message': 'Track scrobbled successfully'})

    except LastFMError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in scrobble: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500

@app.route('/search')
@rate_limit
def search():
    """Search for tracks on Last.fm"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    if len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters long'}), 400

    try:
        params = {
            'method': 'track.search',
            'track': query,
            'api_key': API_KEY,
            'limit': min(int(request.args.get('limit', 10)), 30)
        }

        data = make_lastfm_request(params)

        results = []
        if 'results' in data and 'trackmatches' in data['results']:
            tracks = data['results']['trackmatches']['track']
            # Ensure tracks is always a list
            if isinstance(tracks, dict):
                tracks = [tracks]
            
            for track in tracks:
                results.append({
                    'artist': track.get('artist', ''),
                    'name': track.get('name', ''),
                    'url': track.get('url', ''),
                    'listeners': track.get('listeners', '0')
                })
        
        return jsonify(results)
    
    except LastFMError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/now-playing', methods=['POST'])
@require_auth
@rate_limit
def update_now_playing():
    """Update now playing track"""
    try:
        errors = validate_input(request.form, ['artist', 'track'])
        if errors:
            return jsonify({'success': False, 'errors': errors}), 400

        artist = request.form['artist'].strip()
        track = request.form['track'].strip()
        album = request.form.get('album', '').strip()

        params = {
            'method': 'track.updateNowPlaying',
            'api_key': API_KEY,
            'sk': session['oauth_token'],
            'artist': artist,
            'track': track
        }
        
        if album:
            params['album'] = album
            
        params['api_sig'] = get_api_signature(params)
        
        data = make_lastfm_request(params, method='POST')
        
        return jsonify({'success': True, 'message': 'Now playing updated'})
    
    except LastFMError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating now playing: {e}")
        return jsonify({'success': False, 'error': 'Failed to update now playing'}), 500

@app.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('privacy.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # Ensure API keys are set
    if API_KEY == 'your_api_key_here' or API_SECRET == 'your_api_secret_here':
        logger.warning("Please set LASTFM_API_KEY and LASTFM_API_SECRET environment variables")
    
    # Use debug mode based on environment variable for security
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='127.0.0.1', port=5000)
