from .schema import UsersInsert
from services.exceptions import AuthenticationError, ValidationError
from typing import Dict
import hashlib
import secrets
from .user import UserService

class AuthService:
    """Authentication and authorization"""
    
    def __init__(self):
        self.user_service = UserService()
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hashed.hex()}"
    
    @staticmethod
    def verify_password(password: str, hash_str: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hashed = hash_str.split('$')
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return new_hash.hex() == hashed
        except (ValueError, AttributeError):
            return False

    def signup(self, email: str, name: str, password: str, user_type: str = None) -> Dict:
        """Register new user"""
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        if not email or "@" not in email:
            raise ValidationError("Invalid email format")
        
        user = UsersInsert(
            email_id=email,
            name=name,
            password_hash=self.hash_password(password),
            user_type=user_type
        )
        return self.user_service.create_user(user)
    
    def login(self, email: str, password: str) -> Dict:
        """Authenticate user. Raises AuthenticationError on failure."""
        user = self.user_service.get_user_by_email(email)
        if not user:
            raise AuthenticationError("Invalid credentials")
        
        if not self.verify_password(password, user.get("password_hash", "")):
            raise AuthenticationError("Invalid credentials")
        
        return user