"""Models for WhatsApp session management."""

from datetime import datetime
from app import db

class WhatsAppSession(db.Model):
    """Model for storing WhatsApp session information."""
    
    __tablename__ = 'whatsapp_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    session_id = db.Column(db.String(64), nullable=False, unique=True)
    session_data = db.Column(db.Text, nullable=True)  # Stores serialized session data
    qr_code = db.Column(db.Text, nullable=True)  # Stores base64 encoded QR code
    status = db.Column(db.String(32), default='disconnected')  # connected, disconnected, connecting
    last_connected = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship with devices
    devices = db.relationship('WhatsAppDevice', back_populates='session', cascade='all, delete-orphan')
    
    # Relationship with message queue
    message_queue = db.relationship('MessageQueue', back_populates='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<WhatsAppSession {self.name}:{self.status}>'
    
    def to_dict(self):
        """Convert session to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'session_id': self.session_id,
            'status': self.status,
            'last_connected': self.last_connected.isoformat() if self.last_connected else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'has_qr': bool(self.qr_code)
        }
    
    @classmethod
    def get_active_sessions(cls):
        """Get all active WhatsApp sessions.
        
        Returns:
            List of active WhatsAppSession instances
        """
        return cls.query.filter_by(is_active=True).all()
    
    @classmethod
    def get_session_by_name(cls, name):
        """Get a session by name.
        
        Args:
            name: The session name
            
        Returns:
            WhatsAppSession instance or None if not found
        """
        return cls.query.filter_by(name=name, is_active=True).first()
    
    @classmethod
    def get_session_by_id(cls, session_id):
        """Get a session by session ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            WhatsAppSession instance or None if not found
        """
        return cls.query.filter_by(session_id=session_id, is_active=True).first()


class WhatsAppDevice(db.Model):
    """Model for storing WhatsApp device information."""
    
    __tablename__ = 'whatsapp_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('whatsapp_sessions.id'), nullable=False)
    device_id = db.Column(db.String(64), nullable=False)
    phone_number = db.Column(db.String(32), nullable=True)
    device_name = db.Column(db.String(128), nullable=True)
    platform = db.Column(db.String(32), nullable=True)  # android, ios, web, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with session
    session = db.relationship('WhatsAppSession', back_populates='devices')
    
    def __repr__(self):
        return f'<WhatsAppDevice {self.device_name}:{self.phone_number}>'
    
    def to_dict(self):
        """Convert device to dictionary for API responses."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'device_id': self.device_id,
            'phone_number': self.phone_number,
            'device_name': self.device_name,
            'platform': self.platform,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }