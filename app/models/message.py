"""Message model for storing message history."""

from datetime import datetime
from app import db

class Message(db.Model):
    """Message model for storing message history."""
    
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    platform = db.Column(db.String(20), nullable=False, index=True)
    recipient = db.Column(db.String(64), nullable=False, index=True)
    message_text = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')  # pending, sent, draft, scheduled, failed
    external_id = db.Column(db.String(64))  # ID from external service
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    scheduled_at = db.Column(db.DateTime, nullable=True)  # For scheduled messages
    
    # Relationship with user
    user = db.relationship('User', backref=db.backref('messages', lazy=True))
    
    def __repr__(self):
        return f'<Message {self.id}: {self.platform} to {self.recipient}>'