import os
import time
import hashlib
import logging
import requests
import random
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

# Admin configuration - consistent admin user list
ADMIN_USERS = ['schoolbusgaming', 'admin', 'administrator']

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
            return jsonify({'success': False, 'error': 'Rate limit exceeded. Please try again later.'}), 429
        return f(*args, **kwargs)
    return decorated_function

def is_admin(username):
    """Check if user is an admin"""
    return username and username.lower() in [user.lower() for user in ADMIN_USERS]

def require_admin(f):
    """Decorator to require admin privileges - NO RATE LIMITING for admins"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'oauth_token' not in session or 'user_name' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        if not is_admin(session.get('user_name')):
            return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
        
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

def get_user_info(username):
    """Get user information from Last.fm"""
    try:
        params = {
            'method': 'user.getInfo',
            'user': username,
            'api_key': API_KEY
        }
        
        data = make_lastfm_request(params)
        
        if 'user' in data:
            user = data['user']
            
            # Get the largest available image
            image_url = ''
            if 'image' in user and isinstance(user['image'], list):
                for img in reversed(user['image']):
                    if img.get('#text'):
                        image_url = img['#text']
                        break
            
            return {
                'name': user.get('name', username),
                'realname': user.get('realname', ''),
                'url': user.get('url', ''),
                'image': image_url,
                'playcount': user.get('playcount', '0'),
                'playlists': user.get('playlists', '0'),
                'bootstrap': user.get('bootstrap', '0'),
                'registered': user.get('registered', {}).get('#text', ''),
                'country': user.get('country', ''),
                'age': user.get('age', ''),
                'gender': user.get('gender', ''),
                'subscriber': user.get('subscriber', '0') == '1'
            }
        
        return None
    except LastFMError:
        raise
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise LastFMError("Failed to get user information")

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
            
            # Get and store user info
            try:
                user_info = get_user_info(data['session']['name'])
                if user_info:
                    session['user_info'] = user_info
            except Exception as e:
                logger.warning(f"Could not fetch user info: {e}")
            
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

def get_user_recent_tracks(limit=10, page=1):
    """Get user's recent tracks from Last.fm with pagination"""
    if 'oauth_token' not in session or 'user_name' not in session:
        return []

    try:
        params = {
            'method': 'user.getRecentTracks',
            'user': session.get('user_name'),
            'api_key': API_KEY,
            'limit': min(limit, 50),  # Limit to prevent abuse
            'page': page
        }

        data = make_lastfm_request(params)
        
        result = {
            'tracks': [],
            'total_pages': 1,
            'current_page': page,
            'total_tracks': 0
        }
        
        if 'recenttracks' in data:
            recent_tracks = data['recenttracks']
            
            # Get pagination info
            if '@attr' in recent_tracks:
                attr = recent_tracks['@attr']
                result['total_pages'] = int(attr.get('totalPages', 1))
                result['current_page'] = int(attr.get('page', 1))
                result['total_tracks'] = int(attr.get('total', 0))
            
            # Get tracks
            if 'track' in recent_tracks:
                tracks = recent_tracks['track']
                # Ensure tracks is always a list
                if isinstance(tracks, dict):
                    tracks = [tracks]
                result['tracks'] = tracks
        
        return result
    except LastFMError:
        raise
    except Exception as e:
        logger.error(f"Error getting recent tracks: {e}")
        raise LastFMError("Failed to load recent tracks")

@app.route('/recent-tracks')
@require_auth
@rate_limit
def get_recent_tracks_api():
    """API endpoint to get recent tracks with pagination"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        # Validate inputs
        if page < 1:
            page = 1
        if limit < 1 or limit > 50:
            limit = 20
            
        result = get_user_recent_tracks(limit=limit, page=page)
        
        return jsonify({
            'success': True,
            'tracks': result['tracks'],
            'pagination': {
                'current_page': result['current_page'],
                'total_pages': result['total_pages'],
                'total_tracks': result['total_tracks'],
                'has_next': result['current_page'] < result['total_pages']
            }
        })
        
    except LastFMError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in recent tracks API: {e}")
        return jsonify({'success': False, 'error': 'Failed to load recent tracks'}), 500

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
            
            # Get user info if not already stored
            if 'user_info' not in session:
                try:
                    user_info = get_user_info(session['last_user'])
                    if user_info:
                        session['user_info'] = user_info
                except Exception as e:
                    logger.warning(f"Could not fetch user info: {e}")
        else:
            try:
                auth_url = get_auth_url()
                return render_template('index.html', auth_url=auth_url)
            except LastFMError as e:
                flash(f'Error: {str(e)}', 'error')
                return render_template('index.html')

    # Get user's recent tracks (first page only for initial load)
    try:
        recent_tracks_data = get_user_recent_tracks(limit=10, page=1)
        return render_template('index.html', 
                             recent_tracks=recent_tracks_data['tracks'],
                             pagination=recent_tracks_data,
                             user_name=session.get('user_name'),
                             user_info=session.get('user_info'))
    except LastFMError as e:
        flash(f'Error loading recent tracks: {str(e)}', 'error')
        return render_template('index.html', 
                             user_name=session.get('user_name'),
                             user_info=session.get('user_info'))

# Admin dashboard routes - NO RATE LIMITING for admins
@app.route('/admin')
@require_auth
def admin_dashboard():
    """Admin dashboard page - basic access control"""
    if not is_admin(session.get('user_name')):
        flash('Access denied: Admin privileges required', 'error')
        return redirect(url_for('home'))
    
    return render_template('admin_dashboard.html', 
                         user_name=session.get('user_name'),
                         user_info=session.get('user_info'))

@app.route('/admin/system-stats')
@require_admin  # Using require_admin decorator (no rate limiting)
def admin_system_stats():
    """Get system statistics for admin dashboard"""
    try:
        # Calculate some basic stats
        active_ips = len(rate_limiter.requests.keys())
        total_requests_today = sum(len(reqs) for reqs in rate_limiter.requests.values())
        
        # Get storage info
        storage_used = 0
        try:
            import os
            storage_used = os.path.getsize('tokens.json') / (1024 * 1024) if os.path.exists('tokens.json') else 0
        except:
            storage_used = 0
        
        stats = {
            'active_sessions': random.randint(1, 10),  # Simulated for demo
            'total_requests_today': total_requests_today,
            'active_ips': active_ips,
            'total_users': len(getattr(token_store, 'tokens', {})),
            'storage_used': round(storage_used, 2),
            'rate_limit_config': {
                'requests_per_window': RATE_LIMIT_REQUESTS,
                'window_seconds': RATE_LIMIT_WINDOW
            }
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/rate-limit-stats')
@require_admin  # Using require_admin decorator (no rate limiting)
def admin_rate_limit_stats():
    """Get rate limit statistics for admin dashboard"""
    try:
        rate_limits = {}
        now = datetime.now()
        
        for ip, requests in rate_limiter.requests.items():
            # Clean old requests
            recent_requests = [req_time for req_time in requests 
                             if now - req_time < timedelta(seconds=RATE_LIMIT_WINDOW)]
            
            if recent_requests:
                rate_limits[ip] = {
                    'request_count': len(recent_requests),
                    'last_request': recent_requests[-1].isoformat() if recent_requests else None,
                    'status': 'limited' if len(recent_requests) >= RATE_LIMIT_REQUESTS else 'ok'
                }
        
        return jsonify({'success': True, 'rate_limits': rate_limits})
        
    except Exception as e:
        logger.error(f"Error getting rate limit stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/clear-rate-limits', methods=['POST'])
@require_admin  # Using require_admin decorator (no rate limiting)
def admin_clear_rate_limits():
    """Clear all rate limits - admin only"""
    try:
        rate_limiter.requests.clear()
        logger.info(f"Rate limits cleared by admin user: {session.get('user_name')}")
        return jsonify({'success': True, 'message': 'All rate limits cleared'})
        
    except Exception as e:
        logger.error(f"Error clearing rate limits: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/check-admin')
@require_auth
def check_admin():
    """Check if current user has admin privileges"""
    return jsonify({
        'success': True, 
        'is_admin': is_admin(session.get('user_name')),
        'username': session.get('user_name')
    })

# Continue with other routes (keeping existing functionality)...
@app.route('/user-info')
@require_auth
def get_user_info_endpoint():
    """Get current user information"""
    try:
        if 'user_info' in session:
            return jsonify({'success': True, 'user': session['user_info']})
        
        # Fetch user info if not in session
        user_info = get_user_info(session.get('user_name'))
        if user_info:
            session['user_info'] = user_info
            return jsonify({'success': True, 'user': user_info})
        else:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
    except LastFMError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return jsonify({'success': False, 'error': 'Failed to get user info'}), 500

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
                    'track': track
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
            return jsonify({'success': False, 'error': ', '.join(errors)}), 400

        artist = request.form['artist'].strip()
        track = request.form['track'].strip()
        album = request.form.get('album', '').strip()
        
        # Custom timestamp handling
        custom_time = request.form.get('scrobble_time', '').strip()
        timestamp = int(time.time())  # Default to now
        
        if custom_time:
            try:
                # Parse custom timestamp
                dt = datetime.fromisoformat(custom_time.replace('Z', '+00:00'))
                timestamp = int(dt.timestamp())
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid timestamp format: {custom_time}, using current time")
        
        # Additional validation
        if len(artist) > 200 or len(track) > 200:
            return jsonify({'success': False, 'error': 'Artist and track names must be under 200 characters'}), 400

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
                    'name': track.get('name', ''),
                    'artist': track.get('artist', ''),
                    'url': track.get('url', ''),
                    'listeners': track.get('listeners', '0'),
                    'image': track.get('image', [])
                })
        
        return jsonify(results)
    
    except LastFMError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/dashboard')
@require_auth
def dashboard():
    """Analytics dashboard page"""
    return render_template('dashboard.html', 
                         user_name=session.get('user_name'),
                         user_info=session.get('user_info'))

@app.route('/stats')
@require_auth
@rate_limit
def get_listening_stats():
    """Generate comprehensive listening statistics"""
    try:
        # Get recent tracks for analysis (more for better stats)
        recent_data = get_user_recent_tracks(limit=50, page=1)
        tracks = recent_data.get('tracks', [])
        
        # Calculate unique counts
        unique_artists = set()
        unique_albums = set()
        
        for track in tracks:
            if 'artist' in track:
                unique_artists.add(track['artist'].get('#text', ''))
            if 'album' in track:
                unique_albums.add(track['album'].get('#text', ''))
        
        # Calculate average scrobbles per day (rough estimate)
        total_scrobbles = recent_data.get('total_tracks', 0)
        avg_per_day = 0
        if tracks:
            try:
                oldest_track = tracks[-1]
                if 'date' in oldest_track:
                    oldest_timestamp = int(oldest_track['date']['uts'])
                    days_ago = (time.time() - oldest_timestamp) / (24 * 3600)
                    if days_ago > 0:
                        avg_per_day = round(len(tracks) / days_ago, 1)
            except:
                pass
        
        stats = {
            'total_scrobbles': total_scrobbles,
            'unique_artists': len(unique_artists),
            'unique_albums': len(unique_albums),
            'avg_per_day': avg_per_day,
            'most_active_hour': 14,  # Simplified for demo
            'patterns': {
                'hourly': {str(i): random.randint(0, 10) for i in range(24)},
                'daily': {str(i): random.randint(0, 20) for i in range(7)}
            }
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting listening stats: {e}")
        return jsonify({'success': False, 'error': 'Failed to get listening stats'}), 500

@app.route('/top-artists')
@require_auth
@rate_limit
def get_top_artists():
    """Get user's top artists with time period filtering"""
    try:
        period = request.args.get('period', '7day')
        limit = min(int(request.args.get('limit', 10)), 50)
        
        params = {
            'method': 'user.getTopArtists',
            'user': session.get('user_name'),
            'api_key': API_KEY,
            'period': period,
            'limit': limit
        }
        
        data = make_lastfm_request(params)
        artists = data.get('topartists', {}).get('artist', [])
        
        # Ensure artists is always a list
        if isinstance(artists, dict):
            artists = [artists]
            
        return jsonify({'success': True, 'artists': artists})
        
    except LastFMError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting top artists: {e}")
        return jsonify({'success': False, 'error': 'Failed to get top artists'}), 500

@app.route('/top-tracks')
@require_auth
@rate_limit
def get_top_tracks():
    """Get user's top tracks with time period filtering"""
    try:
        period = request.args.get('period', '7day')
        limit = min(int(request.args.get('limit', 10)), 50)
        
        params = {
            'method': 'user.getTopTracks',
            'user': session.get('user_name'),
            'api_key': API_KEY,
            'period': period,
            'limit': limit
        }
        
        data = make_lastfm_request(params)
        tracks = data.get('toptracks', {}).get('track', [])
        
        # Ensure tracks is always a list
        if isinstance(tracks, dict):
            tracks = [tracks]
            
        return jsonify({'success': True, 'tracks': tracks})
        
    except LastFMError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting top tracks: {e}")
        return jsonify({'success': False, 'error': 'Failed to get top tracks'}), 500

@app.route('/top-albums')
@require_auth
@rate_limit
def get_top_albums():
    """Get user's top albums with time period filtering"""
    try:
        period = request.args.get('period', '7day')
        limit = min(int(request.args.get('limit', 10)), 50)
        
        params = {
            'method': 'user.getTopAlbums',
            'user': session.get('user_name'),
            'api_key': API_KEY,
            'period': period,
            'limit': limit
        }
        
        data = make_lastfm_request(params)
        albums = data.get('topalbums', {}).get('album', [])
        
        # Ensure albums is always a list
        if isinstance(albums, dict):
            albums = [albums]
            
        return jsonify({'success': True, 'albums': albums})
        
    except LastFMError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting top albums: {e}")
        return jsonify({'success': False, 'error': 'Failed to get top albums'}), 500

@app.route('/now-playing', methods=['POST'])
@require_auth
@rate_limit
def update_now_playing():
    """Update now playing track"""
    try:
        errors = validate_input(request.form, ['artist', 'track'])
        if errors:
            return jsonify({'success': False, 'error': ', '.join(errors)}), 400

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
