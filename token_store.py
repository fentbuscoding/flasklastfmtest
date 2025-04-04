import json
import os
from typing import Optional, Dict

class TokenStore:
    def __init__(self, file_path: str = "tokens.json"):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)

    def save_token(self, user_name: str, token: str) -> None:
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            data[user_name] = token
            with open(self.file_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving token: {e}")

    def get_token(self, user_name: str) -> Optional[str]:
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            return data.get(user_name)
        except Exception as e:
            print(f"Error getting token: {e}")
            return None

    def delete_token(self, user_name: str) -> None:
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            if user_name in data:
                del data[user_name]
            with open(self.file_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error deleting token: {e}")