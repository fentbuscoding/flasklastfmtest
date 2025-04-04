import os
import time
import hashlib
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from urllib.parse import urlencode
from token_store import TokenStore

app = Flask(__name__)
app.secret_key = os.urandom(24)
token_store = TokenStore()

API_KEY = 'API_KEY'
API_SECRET = 'API_KEY'

# Add authentication routes and helper functions
def get_auth_url():
    callback_url = url_for('callback', _external=True)
    params = {
        'api_key': API_KEY,
        'cb': callback_url
    }
    return f"http://www.last.fm/api/auth/?{urlencode(params)}"

def get_api_signature(params):
    # Sort parameters and concatenate them
    string_to_sign = ''.join([f"{k}{params[k]}" for k in sorted(params.keys())])
    string_to_sign += API_SECRET
    # Calculate md5 hash
    return hashlib.md5(string_to_sign.encode('utf-8')).hexdigest()

@app.route('/callback')
def callback():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('home'))

    # Get session key
    params = {
        'api_key': API_KEY,
        'method': 'auth.getSession',
        'token': token,
    }
    params['api_sig'] = get_api_signature(params)
    params['format'] = 'json'

    response = requests.get('https://ws.audioscrobbler.com/2.0/', params=params)
    data = response.json()

    if 'session' in data:
        session['oauth_token'] = data['session']['key']
        session['user_name'] = data['session']['name']
        # Save token to persistent storage
        token_store.save_token(data['session']['name'], data['session']['key'])
        return redirect(url_for('home'))
    return render_template('index.html', error="Authentication failed")

@app.route('/logout')
def logout():
    if 'user_name' in session:
        token_store.delete_token(session['user_name'])
    session.clear()
    return redirect(url_for('home'))

@app.route('/')
def home():
    if 'oauth_token' not in session and 'user_name' not in session:
        stored_token = None
        if 'last_user' in session:
            stored_token = token_store.get_token(session['last_user'])
        
        if stored_token:
            session['oauth_token'] = stored_token
            session['user_name'] = session['last_user']
        else:
            auth_url = get_auth_url()
            return render_template('index.html', auth_url=auth_url)

    # Get user's recent tracks
    recent_tracks = get_user_recent_tracks()
    return render_template('index.html', 
                         recent_tracks=recent_tracks,
                         user_name=session.get('user_name'),
                         auth_url=None)

def get_user_recent_tracks():
    if 'oauth_token' not in session:
        return []

    url = 'https://ws.audioscrobbler.com/2.0/'
    params = {
        'method': 'user.getRecentTracks',
        'user': session.get('user_name'),
        'api_key': API_KEY,
        'format': 'json',
        'limit': 5
    }

    response = requests.get(url, params=params)
    data = response.json()

    if 'recenttracks' in data:
        return data['recenttracks']['track']
    return []

@app.route('/scrobble', methods=['POST'])
def scrobble():
    if 'oauth_token' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        artist = request.form['artist']
        track = request.form['track']

        params = {
            'method': 'track.scrobble',
            'api_key': API_KEY,
            'sk': session['oauth_token'],
            'artist': artist,
            'track': track,
            'timestamp': int(time.time())
        }
        
        params['api_sig'] = get_api_signature(params)
        params['format'] = 'json'

        response = requests.post('https://ws.audioscrobbler.com/2.0/', params=params)
        data = response.json()

        if 'error' in data:
            return jsonify({'success': False, 'error': data.get('message', 'Scrobble failed')}), 400
        
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    params = {
        'method': 'track.search',
        'track': query,
        'api_key': API_KEY,
        'format': 'json',
        'limit': 5
    }

    response = requests.get('https://ws.audioscrobbler.com/2.0/', params=params)
    data = response.json()

    results = []
    if 'results' in data and 'trackmatches' in data['results']:
        for track in data['results']['trackmatches']['track']:
            results.append({
                'artist': track['artist'],
                'name': track['name']
            })
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
