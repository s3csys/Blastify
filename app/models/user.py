"""User model for authentication and authorization."""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
from app import db
from time import time
import jwt
from flask import current_app
from flask_login import UserMixin  # Add this import

class User(db.Model, UserMixin):  # Add UserMixin here
    """User model for authentication and authorization."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # 2FA fields
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    
    # Add property for initials
    @property
    def initials(self):
        """Get user initials for avatar."""
        if not self.username:
            return '?'
        return self.username[0].upper()
    
    # Add property for name
    @property
    def name(self):
        """Get user's full name or username."""
        return self.username
    
    # Add property for role
    @property
    def role(self):
        """Get user's role."""
        return "User"  # You can implement proper role logic later
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Set the user's password hash.
        
        Args:
            password: The plain text password to hash
        """
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check if the provided password matches the hash.
        
        Args:
            password: The plain text password to check
            
        Returns:
            True if the password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def enable_2fa(self):
        """Enable two-factor authentication for the user.
        
        Returns:
            The secret key for setting up 2FA
        """
        self.two_factor_secret = pyotp.random_base32()
        self.two_factor_enabled = True
        return self.two_factor_secret
    
    def disable_2fa(self):
        """Disable two-factor authentication for the user."""
        self.two_factor_secret = None
        self.two_factor_enabled = False
    
    def verify_2fa(self, token):
        """Verify a 2FA token.
        
        Args:
            token: The token to verify
            
        Returns:
            True if the token is valid, False otherwise
        """
        if not self.two_factor_enabled or not self.two_factor_secret:
            return False
        
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(token)

# Add these methods to your User class
def generate_reset_token(self, expires_in=3600):
    """Generate a token for password reset."""
    return jwt.encode(
        {'reset_password': self.id, 'exp': time() + expires_in},
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

@staticmethod
def verify_reset_token(token):
    """Verify the reset token and return the user."""
    try:
        id = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )['reset_password']
    except:
        return None
    return User.query.get(id)