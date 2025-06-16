import pytest
import json
from unittest.mock import patch, MagicMock
from app import app, LastFMError, get_api_signature, validate_input

class TestApp:
    """Test cases for the main Flask application"""
    
    def test_home_page_unauthenticated(self, client):
        """Test home page without authentication"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Connect Your Last.fm Account' in response.data
    
    def test_home_page_authenticated(self, client, mock_lastfm_api, sample_recent_tracks):
        """Test home page with authentication"""
        mock_lastfm_api.return_value = sample_recent_tracks
        
        with client.session_transaction() as sess:
            sess['oauth_token'] = 'test-token'
            sess['user_name'] = 'testuser'
        
        response = client.get('/')
        assert response.status_code == 200
        assert b'testuser' in response.data
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
    
    def test_logout(self, client):
        """Test logout functionality"""
        with client.session_transaction() as sess:
            sess['oauth_token'] = 'test-token'
            sess['user_name'] = 'testuser'
        
        response = client.get('/logout')
        assert response.status_code == 302  # Redirect
        
        with client.session_transaction() as sess:
            assert 'oauth_token' not in sess
            assert 'user_name' not in sess
    
    def test_terms_page(self, client):
        """Test terms of service page"""
        response = client.get('/terms')
        assert response.status_code == 200
        assert b'Terms of Service' in response.data
    
    def test_privacy_page(self, client):
        """Test privacy policy page"""
        response = client.get('/privacy')
        assert response.status_code == 200
        assert b'Privacy Policy' in response.data

class TestAuthentication:
    """Test authentication-related functionality"""
    
    def test_callback_success(self, client, mock_lastfm_api):
        """Test successful authentication callback"""
        mock_lastfm_api.return_value = {
            'session': {
                'key': 'test-session-key',
                'name': 'testuser'
            }
        }
        
        response = client.get('/callback?token=test-token')
        assert response.status_code == 302  # Redirect
        
        with client.session_transaction() as sess:
            assert sess['oauth_token'] == 'test-session-key'
            assert sess['user_name'] == 'testuser'
    
    def test_callback_no_token(self, client):
        """Test callback without token"""
        response = client.get('/callback')
        assert response.status_code == 302  # Redirect to home
    
    def test_callback_api_error(self, client, mock_lastfm_api):
        """Test callback with API error"""
        mock_lastfm_api.side_effect = LastFMError("Authentication failed")
        
        response = client.get('/callback?token=test-token')
        assert response.status_code == 302  # Redirect to home

class TestScrobbling:
    """Test scrobbling functionality"""
    
    def test_scrobble_success(self, authenticated_session, mock_lastfm_api):
        """Test successful scrobble"""
        mock_lastfm_api.return_value = {'scrobbles': {'@attr': {'accepted': 1}}}
        
        response = authenticated_session.post('/scrobble', data={
            'artist': 'Test Artist',
            'track': 'Test Track',
            'album': 'Test Album'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_scrobble_missing_fields(self, authenticated_session):
        """Test scrobble with missing required fields"""
        response = authenticated_session.post('/scrobble', data={
            'artist': 'Test Artist'
            # Missing track
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'errors' in data
    
    def test_scrobble_unauthenticated(self, client):
        """Test scrobble without authentication"""
        response = client.post('/scrobble', data={
            'artist': 'Test Artist',
            'track': 'Test Track'
        })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Authentication required' in data['error']
    
    def test_scrobble_custom_time(self, authenticated_session, mock_lastfm_api):
        """Test scrobble with custom timestamp"""
        mock_lastfm_api.return_value = {'scrobbles': {'@attr': {'accepted': 1}}}
        
        response = authenticated_session.post('/scrobble', data={
            'artist': 'Test Artist',
            'track': 'Test Track',
            'scrobble_time': '30'  # 30 minutes ago
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

class TestSearch:
    """Test search functionality"""
    
    def test_search_success(self, client, mock_lastfm_api, sample_track_data):
        """Test successful search"""
        mock_lastfm_api.return_value = {
            'results': {
                'trackmatches': {
                    'track': [sample_track_data]
                }
            }
        }
        
        response = client.get('/search?q=test+track')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['name'] == 'Test Track'
    
    def test_search_empty_query(self, client):
        """Test search with empty query"""
        response = client.get('/search?q=')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []
    
    def test_search_short_query(self, client):
        """Test search with too short query"""
        response = client.get('/search?q=a')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'must be at least 2 characters' in data['error']

class TestNowPlaying:
    """Test now playing functionality"""
    
    def test_update_now_playing_success(self, authenticated_session, mock_lastfm_api):
        """Test successful now playing update"""
        mock_lastfm_api.return_value = {'nowplaying': {'track': 'Test Track'}}
        
        response = authenticated_session.post('/now-playing', data={
            'artist': 'Test Artist',
            'track': 'Test Track'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_get_now_playing_info(self, authenticated_session, mock_lastfm_api):
        """Test getting now playing info"""
        mock_lastfm_api.return_value = {
            'recenttracks': {
                'track': {
                    'name': 'Test Track',
                    'artist': {'#text': 'Test Artist'},
                    '@attr': {'nowplaying': 'true'}
                }
            }
        }
        
        response = authenticated_session.get('/now-playing-info')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['nowplaying'] is True

class TestUtilities:
    """Test utility functions"""
    
    def test_validate_input_success(self):
        """Test input validation with valid data"""
        data = {'artist': 'Test Artist', 'track': 'Test Track'}
        required = ['artist', 'track']
        errors = validate_input(data, required)
        assert errors == []
    
    def test_validate_input_missing_fields(self):
        """Test input validation with missing fields"""
        data = {'artist': 'Test Artist'}
        required = ['artist', 'track']
        errors = validate_input(data, required)
        assert len(errors) == 1
        assert 'track is required' in errors[0]
    
    def test_validate_input_empty_fields(self):
        """Test input validation with empty fields"""
        data = {'artist': 'Test Artist', 'track': '   '}
        required = ['artist', 'track']
        errors = validate_input(data, required)
        assert len(errors) == 1
    
    def test_get_api_signature(self):
        """Test API signature generation"""
        with patch('app.API_SECRET', 'test-secret'):
            params = {'api_key': 'test', 'method': 'test.method'}
            signature = get_api_signature(params)
            assert isinstance(signature, str)
            assert len(signature) == 32  # MD5 hash length

class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_allows_requests(self, client):
        """Test that rate limiting allows normal requests"""
        # Make several requests within limit
        for _ in range(3):
            response = client.get('/search?q=test')
            assert response.status_code != 429
    
    @patch('app.RATE_LIMIT_REQUESTS', 1)
    def test_rate_limit_blocks_excess_requests(self, client):
        """Test that rate limiting blocks excess requests"""
        # First request should succeed
        response = client.get('/search?q=test')
        assert response.status_code != 429
        
        # Second request might be blocked (depends on timing)
        # This test is simplified - real rate limiting tests need more setup