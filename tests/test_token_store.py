import pytest
import os
import tempfile
import json
from datetime import datetime, timedelta
from token_store import TokenStore, TokenStoreError

class TestTokenStore:
    """Test cases for the TokenStore class"""
    
    def test_init_creates_file(self):
        """Test that TokenStore creates file if it doesn't exist"""
        with tempfile.NamedTemporaryFile(delete=True) as f:
            temp_file = f.name
        
        # File should not exist now
        assert not os.path.exists(temp_file)
        
        # Create TokenStore - should create file
        store = TokenStore(file_path=temp_file)
        assert os.path.exists(temp_file)
        
        # Cleanup
        os.unlink(temp_file)
    
    def test_save_and_get_token(self, test_token_store):
        """Test saving and retrieving a token"""
        user = 'testuser'
        token = 'test-token-123'
        
        # Save token
        result = test_token_store.save_token(user, token)
        assert result is True
        
        # Retrieve token
        retrieved = test_token_store.get_token(user)
        assert retrieved == token
    
    def test_save_token_with_expiration(self, test_token_store):
        """Test saving a token with expiration"""
        user = 'testuser'
        token = 'test-token-123'
        
        # Save token with 1 day expiration
        result = test_token_store.save_token(user, token, expires_in_days=1)
        assert result is True
        
        # Token should be retrievable
        retrieved = test_token_store.get_token(user)
        assert retrieved == token
        
        # Check token info
        info = test_token_store.get_token_info(user)
        assert info is not None
        assert info['expires_at'] is not None
        assert info['is_expired'] is False
    
    def test_delete_token(self, test_token_store):
        """Test deleting a token"""
        user = 'testuser'
        token = 'test-token-123'
        
        # Save and verify token exists
        test_token_store.save_token(user, token)
        assert test_token_store.get_token(user) == token
        
        # Delete token
        result = test_token_store.delete_token(user)
        assert result is True
        
        # Token should no longer exist
        assert test_token_store.get_token(user) is None
    
    def test_delete_nonexistent_token(self, test_token_store):
        """Test deleting a token that doesn't exist"""
        result = test_token_store.delete_token('nonexistent')
        assert result is False
    
    def test_list_users(self, test_token_store):
        """Test listing users with tokens"""
        users = ['user1', 'user2', 'user3']
        
        # Initially empty
        assert test_token_store.list_users() == []
        
        # Add users
        for user in users:
            test_token_store.save_token(user, f'token-{user}')
        
        # Check list
        user_list = test_token_store.list_users()
        assert len(user_list) == 3
        assert all(user in user_list for user in users)
    
    def test_get_token_info(self, test_token_store):
        """Test getting token information"""
        user = 'testuser'
        token = 'test-token-123'
        
        # No token initially
        info = test_token_store.get_token_info(user)
        assert info is None
        
        # Save token
        test_token_store.save_token(user, token)
        
        # Get info
        info = test_token_store.get_token_info(user)
        assert info is not None
        assert 'created_at' in info
        assert 'expires_at' in info
        assert 'last_used' in info
        assert 'is_expired' in info
        assert info['is_expired'] is False
    
    def test_expired_token_cleanup(self, test_token_store):
        """Test that expired tokens are cleaned up"""
        user = 'testuser'
        token = 'test-token-123'
        
        # Manually create an expired token
        expired_date = (datetime.now() - timedelta(days=1)).isoformat()
        test_token_store._cache[user] = {
            'token': token,
            'created_at': expired_date,
            'expires_at': expired_date,
            'last_used': expired_date
        }
        test_token_store._save_data(test_token_store._cache)
        
        # Try to get token - should return None due to expiration
        retrieved = test_token_store.get_token(user)
        assert retrieved is None
    
    def test_clear_all_tokens(self, test_token_store):
        """Test clearing all tokens"""
        # Add some tokens
        test_token_store.save_token('user1', 'token1')
        test_token_store.save_token('user2', 'token2')
        
        # Verify tokens exist
        assert len(test_token_store.list_users()) == 2
        
        # Clear all
        result = test_token_store.clear_all_tokens()
        assert result is True
        
        # Verify all cleared
        assert len(test_token_store.list_users()) == 0
    
    def test_len_and_contains(self, test_token_store):
        """Test __len__ and __contains__ methods"""
        # Initially empty
        assert len(test_token_store) == 0
        assert 'user1' not in test_token_store
        
        # Add token
        test_token_store.save_token('user1', 'token1')
        
        # Check
        assert len(test_token_store) == 1
        assert 'user1' in test_token_store
        assert 'user2' not in test_token_store
    
    def test_encryption_decryption(self, test_token_store):
        """Test that tokens are properly encrypted"""
        user = 'testuser'
        token = 'test-token-123'
        
        # Save token
        test_token_store.save_token(user, token)
        
        # Read raw file content
        with open(test_token_store.file_path, 'r') as f:
            raw_data = json.load(f)
        
        # Token should be encrypted in file
        stored_token = raw_data[user]['token']
        assert stored_token != token  # Should be encrypted
        
        # But retrieval should return original
        retrieved = test_token_store.get_token(user)
        assert retrieved == token
    
    def test_invalid_input_handling(self, test_token_store):
        """Test handling of invalid inputs"""
        # Empty username
        assert test_token_store.save_token('', 'token') is False
        assert test_token_store.get_token('') is None
        
        # Empty token
        assert test_token_store.save_token('user', '') is False
    
    def test_backup_and_restore(self, test_token_store):
        """Test backup and restore functionality"""
        user = 'testuser'
        token = 'test-token-123'
        
        # Save token (creates backup)
        test_token_store.save_token(user, token)
        
        # Backup file should exist
        assert os.path.exists(test_token_store.backup_path)
        
        # Corrupt main file
        with open(test_token_store.file_path, 'w') as f:
            f.write('invalid json')
        
        # Create new store instance - should restore from backup
        new_store = TokenStore(file_path=test_token_store.file_path)
        retrieved = new_store.get_token(user)
        assert retrieved == token