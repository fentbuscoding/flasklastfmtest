import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from app import app
from token_store import TokenStore

@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    # Create a temporary file for testing database
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield client
    
    os.close(db_fd)
    os.unlink(app.config['DATABASE'])

@pytest.fixture
def mock_lastfm_api():
    """Mock Last.fm API responses"""
    with patch('app.make_lastfm_request') as mock_request:
        yield mock_request

@pytest.fixture
def test_token_store():
    """Create a test token store with temporary file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name
    
    store = TokenStore(file_path=temp_file)
    yield store
    
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)

@pytest.fixture
def authenticated_session(client):
    """Create an authenticated session"""
    with client.session_transaction() as sess:
        sess['oauth_token'] = 'test-token'
        sess['user_name'] = 'testuser'
    return client

@pytest.fixture
def sample_track_data():
    """Sample track data for testing"""
    return {
        'artist': 'Test Artist',
        'name': 'Test Track',
        'album': 'Test Album',
        'listeners': '12345',
        'url': 'https://last.fm/music/test'
    }

@pytest.fixture
def sample_recent_tracks():
    """Sample recent tracks response"""
    return {
        'recenttracks': {
            'track': [
                {
                    'name': 'Test Track 1',
                    'artist': {'#text': 'Test Artist 1'},
                    'album': {'#text': 'Test Album 1'},
                    'date': {'#text': '01 Jan 2025, 12:00'},
                    'url': 'https://last.fm/music/test1'
                },
                {
                    'name': 'Test Track 2',
                    'artist': {'#text': 'Test Artist 2'},
                    'album': {'#text': 'Test Album 2'},
                    '@attr': {'nowplaying': 'true'},
                    'url': 'https://last.fm/music/test2'
                }
            ]
        }
    }