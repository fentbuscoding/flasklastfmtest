import json
import os
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)

class TokenStoreError(Exception):
    """Custom exception for token store operations"""
    pass

class TokenStore:
    """
    Secure token storage with encryption, expiration, and thread safety.
    """
    
    def __init__(self, file_path: str = "tokens.json", encryption_key: Optional[str] = None):
        self.file_path = file_path
        self.backup_path = f"{file_path}.backup"
        self._lock = threading.RLock()
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache TTL
        
        # Initialize encryption
        self._init_encryption(encryption_key)
        
        # Ensure file exists
        self._ensure_file_exists()
        
        # Load initial cache
        self._refresh_cache()

    def _init_encryption(self, encryption_key: Optional[str] = None) -> None:
        """Initialize encryption using provided key or environment variable"""
        try:
            if encryption_key:
                key = encryption_key.encode()
            else:
                key = os.environ.get('TOKEN_ENCRYPTION_KEY', '').encode()
            
            if not key:
                # Generate a key from a password (you should set this in environment)
                password = os.environ.get('SECRET_KEY', 'default-secret-key').encode()
                salt = b'last-fm-token-salt'  # In production, use random salt
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
            elif len(key) < 32:
                # Extend key if too short
                key = key.ljust(32, b'0')
            
            self._cipher = Fernet(base64.urlsafe_b64encode(key[:32]))
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise TokenStoreError(f"Encryption initialization failed: {e}")

    def _ensure_file_exists(self) -> None:
        """Ensure the token file exists with proper permissions"""
        try:
            if not os.path.exists(self.file_path):
                with open(self.file_path, 'w') as f:
                    json.dump({}, f, indent=2)
                
                # Set restrictive permissions (owner read/write only)
                os.chmod(self.file_path, 0o600)
                logger.info(f"Created token store file: {self.file_path}")
            
            # Verify file permissions
            file_stat = os.stat(self.file_path)
            if file_stat.st_mode & 0o077:  # Check if group/other have any permissions
                logger.warning(f"Token file has overly permissive permissions: {oct(file_stat.st_mode)}")
                os.chmod(self.file_path, 0o600)
                
        except Exception as e:
            logger.error(f"Failed to ensure file exists: {e}")
            raise TokenStoreError(f"File creation failed: {e}")

    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            return self._cipher.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise TokenStoreError(f"Data encryption failed: {e}")

    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            return self._cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise TokenStoreError(f"Data decryption failed: {e}")

    def _create_backup(self) -> None:
        """Create a backup of the current token file"""
        try:
            if os.path.exists(self.file_path):
                import shutil
                shutil.copy2(self.file_path, self.backup_path)
                logger.debug(f"Created backup: {self.backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")

    def _restore_from_backup(self) -> None:
        """Restore from backup if main file is corrupted"""
        try:
            if os.path.exists(self.backup_path):
                import shutil
                shutil.copy2(self.backup_path, self.file_path)
                logger.info(f"Restored from backup: {self.backup_path}")
            else:
                # Create empty file if no backup exists
                with open(self.file_path, 'w') as f:
                    json.dump({}, f, indent=2)
                logger.info("Created new empty token store")
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            raise TokenStoreError(f"Backup restoration failed: {e}")

    def _load_data(self) -> Dict[str, Any]:
        """Load and decrypt data from file"""
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            # Decrypt tokens if they exist
            decrypted_data = {}
            for user, user_data in data.items():
                if isinstance(user_data, dict):
                    decrypted_data[user] = {
                        'token': self._decrypt_data(user_data['token']),
                        'created_at': user_data.get('created_at'),
                        'expires_at': user_data.get('expires_at'),
                        'last_used': user_data.get('last_used')
                    }
                else:
                    # Legacy format - just the token
                    decrypted_data[user] = {
                        'token': self._decrypt_data(user_data),
                        'created_at': datetime.now().isoformat(),
                        'expires_at': None,
                        'last_used': None
                    }
            
            return decrypted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            self._restore_from_backup()
            return self._load_data()  # Retry after restore
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise TokenStoreError(f"Data loading failed: {e}")

    def _save_data(self, data: Dict[str, Any]) -> None:
        """Encrypt and save data to file"""
        try:
            # Create backup before saving
            self._create_backup()
            
            # Encrypt tokens
            encrypted_data = {}
            for user, user_data in data.items():
                encrypted_data[user] = {
                    'token': self._encrypt_data(user_data['token']),
                    'created_at': user_data.get('created_at'),
                    'expires_at': user_data.get('expires_at'),
                    'last_used': user_data.get('last_used')
                }
            
            # Write to temporary file first
            temp_path = f"{self.file_path}.tmp"
            with open(temp_path, 'w') as f:
                json.dump(encrypted_data, f, indent=2)
            
            # Atomic move
            os.replace(temp_path, self.file_path)
            
            # Set proper permissions
            os.chmod(self.file_path, 0o600)
            
            logger.debug(f"Saved {len(data)} tokens to {self.file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            # Clean up temp file if it exists
            if os.path.exists(f"{self.file_path}.tmp"):
                os.remove(f"{self.file_path}.tmp")
            raise TokenStoreError(f"Data saving failed: {e}")

    def _refresh_cache(self) -> None:
        """Refresh the internal cache"""
        try:
            self._cache = self._load_data()
            self._cache_timestamp = datetime.now()
            logger.debug("Cache refreshed")
        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")
            self._cache = {}

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache_timestamp:
            return False
        return datetime.now() - self._cache_timestamp < timedelta(seconds=self._cache_ttl)

    def _clean_expired_tokens(self) -> None:
        """Remove expired tokens"""
        try:
            with self._lock:
                if not self._is_cache_valid():
                    self._refresh_cache()
                
                now = datetime.now()
                expired_users = []
                
                for user, user_data in self._cache.items():
                    expires_at = user_data.get('expires_at')
                    if expires_at:
                        try:
                            exp_date = datetime.fromisoformat(expires_at)
                            if now > exp_date:
                                expired_users.append(user)
                        except ValueError:
                            logger.warning(f"Invalid expiration date for user {user}")
                
                if expired_users:
                    for user in expired_users:
                        del self._cache[user]
                    self._save_data(self._cache)
                    logger.info(f"Cleaned {len(expired_users)} expired tokens")
                    
        except Exception as e:
            logger.error(f"Failed to clean expired tokens: {e}")

    def save_token(self, user_name: str, token: str, expires_in_days: Optional[int] = None) -> bool:
        """
        Save a token for a user with optional expiration.
        
        Args:
            user_name: The username
            token: The token to save
            expires_in_days: Optional expiration in days
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not user_name or not token:
                raise ValueError("Username and token cannot be empty")
            
            with self._lock:
                if not self._is_cache_valid():
                    self._refresh_cache()
                
                now = datetime.now()
                expires_at = None
                if expires_in_days:
                    expires_at = (now + timedelta(days=expires_in_days)).isoformat()
                
                self._cache[user_name] = {
                    'token': token,
                    'created_at': now.isoformat(),
                    'expires_at': expires_at,
                    'last_used': now.isoformat()
                }
                
                self._save_data(self._cache)
                logger.info(f"Saved token for user: {user_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save token for {user_name}: {e}")
            return False

    def get_token(self, user_name: str) -> Optional[str]:
        """
        Get a token for a user.
        
        Args:
            user_name: The username
            
        Returns:
            Optional[str]: The token if found, None otherwise
        """
        try:
            if not user_name:
                return None
            
            with self._lock:
                if not self._is_cache_valid():
                    self._refresh_cache()
                
                user_data = self._cache.get(user_name)
                if not user_data:
                    return None
                
                # Check if token is expired
                expires_at = user_data.get('expires_at')
                if expires_at:
                    try:
                        exp_date = datetime.fromisoformat(expires_at)
                        if datetime.now() > exp_date:
                            logger.info(f"Token expired for user: {user_name}")
                            self.delete_token(user_name)
                            return None
                    except ValueError:
                        logger.warning(f"Invalid expiration date for user {user_name}")
                
                # Update last used timestamp
                user_data['last_used'] = datetime.now().isoformat()
                self._save_data(self._cache)
                
                logger.debug(f"Retrieved token for user: {user_name}")
                return user_data['token']
                
        except Exception as e:
            logger.error(f"Failed to get token for {user_name}: {e}")
            return None

    def delete_token(self, user_name: str) -> bool:
        """
        Delete a token for a user.
        
        Args:
            user_name: The username
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not user_name:
                return False
            
            with self._lock:
                if not self._is_cache_valid():
                    self._refresh_cache()
                
                if user_name in self._cache:
                    del self._cache[user_name]
                    self._save_data(self._cache)
                    logger.info(f"Deleted token for user: {user_name}")
                    return True
                else:
                    logger.debug(f"No token found for user: {user_name}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete token for {user_name}: {e}")
            return False

    def list_users(self) -> list:
        """
        Get a list of all users with stored tokens.
        
        Returns:
            list: List of usernames
        """
        try:
            with self._lock:
                if not self._is_cache_valid():
                    self._refresh_cache()
                
                # Clean expired tokens first
                self._clean_expired_tokens()
                
                return list(self._cache.keys())
                
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []

    def get_token_info(self, user_name: str) -> Optional[Dict[str, Any]]:
        """
        Get token information for a user (without the actual token).
        
        Args:
            user_name: The username
            
        Returns:
            Optional[Dict]: Token metadata if found, None otherwise
        """
        try:
            if not user_name:
                return None
            
            with self._lock:
                if not self._is_cache_valid():
                    self._refresh_cache()
                
                user_data = self._cache.get(user_name)
                if not user_data:
                    return None
                
                return {
                    'created_at': user_data.get('created_at'),
                    'expires_at': user_data.get('expires_at'),
                    'last_used': user_data.get('last_used'),
                    'is_expired': self._is_token_expired(user_data)
                }
                
        except Exception as e:
            logger.error(f"Failed to get token info for {user_name}: {e}")
            return None

    def _is_token_expired(self, user_data: Dict[str, Any]) -> bool:
        """Check if a token is expired"""
        expires_at = user_data.get('expires_at')
        if not expires_at:
            return False
        
        try:
            exp_date = datetime.fromisoformat(expires_at)
            return datetime.now() > exp_date
        except ValueError:
            return False

    def cleanup_expired_tokens(self) -> int:
        """
        Clean up all expired tokens.
        
        Returns:
            int: Number of tokens cleaned up
        """
        try:
            with self._lock:
                if not self._is_cache_valid():
                    self._refresh_cache()
                
                initial_count = len(self._cache)
                self._clean_expired_tokens()
                final_count = len(self._cache)
                
                cleaned_count = initial_count - final_count
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired tokens")
                
                return cleaned_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {e}")
            return 0

    def clear_all_tokens(self) -> bool:
        """
        Clear all stored tokens.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._lock:
                self._cache = {}
                self._save_data(self._cache)
                logger.info("Cleared all tokens")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear all tokens: {e}")
            return False

    def __len__(self) -> int:
        """Return the number of stored tokens"""
        try:
            with self._lock:
                if not self._is_cache_valid():
                    self._refresh_cache()
                return len(self._cache)
        except Exception:
            return 0

    def __contains__(self, user_name: str) -> bool:
        """Check if a user has a stored token"""
        return self.get_token(user_name) is not None

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            # Clean up expired tokens on exit
            self.cleanup_expired_tokens()
        except Exception:
            pass  # Ignore errors during cleanup