# utils/auth_store.py
import threading
from typing import Dict, Any, Optional

class AuthStore:
    """Thread-safe auth storage that works across async boundaries."""
    
    def __init__(self):
        self._storage: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def set(self, auth: Dict[str, Any]):
        """Store auth globally (thread-safe)."""
        with self._lock:
            self._storage = dict(auth)
            print(f"[AUTH_STORE] Set: user_id={auth.get('user_id')}, has_token={bool(auth.get('token'))}, thread={threading.current_thread().name}")
    
    def get(self) -> Dict[str, Any]:
        """Retrieve auth (thread-safe)."""
        with self._lock:
            auth = dict(self._storage)
            print(f"[AUTH_STORE] Get: user_id={auth.get('user_id')}, has_token={bool(auth.get('token'))}, thread={threading.current_thread().name}")
            return auth
    
    def clear(self):
        """Clear stored auth."""
        with self._lock:
            self._storage = {}
            print(f"[AUTH_STORE] Cleared, thread={threading.current_thread().name}")

# Global singleton
_auth_store = AuthStore()

def get_auth_store() -> AuthStore:
    return _auth_store