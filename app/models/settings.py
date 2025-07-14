"""Settings model for storing application settings."""

from datetime import datetime
from app import db

class Settings(db.Model):
    """Settings model for storing application settings."""
    
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    settings_type = db.Column(db.String(50), nullable=False)  # 'general', 'notification', etc.
    settings_key = db.Column(db.String(100), nullable=False)
    settings_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with User model
    user = db.relationship('User', backref='settings')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'settings_type', 'settings_key', name='_user_settings_uc'),)
    
    def __repr__(self):
        return f'<Settings {self.id}: {self.settings_type}.{self.settings_key}={self.settings_value[:20]}...>'
    
    @classmethod
    def get_setting(cls, user_id, settings_type, settings_key, default=None):
        """Get a setting value for a user.
        
        Args:
            user_id: The user ID
            settings_type: The type of setting (e.g., 'general', 'notification')
            settings_key: The setting key
            default: Default value if setting doesn't exist
            
        Returns:
            The setting value or default
        """
        setting = cls.query.filter_by(
            user_id=user_id,
            settings_type=settings_type,
            settings_key=settings_key
        ).first()
        
        if setting:
            return setting.settings_value
        return default
    
    @classmethod
    def set_setting(cls, user_id, settings_type, settings_key, settings_value):
        """Set a setting value for a user.
        
        Args:
            user_id: The user ID
            settings_type: The type of setting (e.g., 'general', 'notification')
            settings_key: The setting key
            settings_value: The setting value
            
        Returns:
            The setting object
        """
        setting = cls.query.filter_by(
            user_id=user_id,
            settings_type=settings_type,
            settings_key=settings_key
        ).first()
        
        if setting:
            setting.settings_value = settings_value
        else:
            setting = cls(
                user_id=user_id,
                settings_type=settings_type,
                settings_key=settings_key,
                settings_value=settings_value
            )
            db.session.add(setting)
        
        db.session.commit()
        return setting
    
    @classmethod
    def get_settings_by_type(cls, user_id, settings_type):
        """Get all settings of a specific type for a user.
        
        Args:
            user_id: The user ID
            settings_type: The type of setting (e.g., 'general', 'notification')
            
        Returns:
            Dictionary of settings
        """
        settings = cls.query.filter_by(
            user_id=user_id,
            settings_type=settings_type
        ).all()
        
        return {s.settings_key: s.settings_value for s in settings}