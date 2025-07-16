"""Models for message queue and templates."""

from datetime import datetime
from app import db

class MessageTemplate(db.Model):
    """Model for storing message templates."""
    
    __tablename__ = 'message_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(512), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('message_template_categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship with category
    category = db.relationship('MessageTemplateCategory', back_populates='templates')
    
    def __repr__(self):
        return f'<MessageTemplate {self.name}>'
    
    def to_dict(self):
        """Convert template to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'media_url': self.media_url,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active
        }


class MessageQueue(db.Model):
    """Model for storing message queue."""
    
    __tablename__ = 'message_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('whatsapp_sessions.id'), nullable=False)
    recipient = db.Column(db.String(32), nullable=False)  # Phone number
    message = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(512), nullable=True)
    priority = db.Column(db.Integer, default=0)  # Higher number = higher priority
    status = db.Column(db.String(32), default='pending')  # pending, processing, sent, failed
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    scheduled_at = db.Column(db.DateTime, nullable=True)  # For scheduled messages
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with session
    session = db.relationship('WhatsAppSession', back_populates='message_queue')
    
    # Relationship with message status
    status_updates = db.relationship('MessageStatus', back_populates='message', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<MessageQueue {self.id}:{self.status}>'
    
    def to_dict(self):
        """Convert queue item to dictionary for API responses."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'recipient': self.recipient,
            'message': self.message,
            'media_url': self.media_url,
            'priority': self.priority,
            'status': self.status,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def get_pending_messages(cls, session_id=None, limit=50):
        """Get pending messages for processing.
        
        Args:
            session_id: Optional session ID to filter by
            limit: Maximum number of messages to return
            
        Returns:
            List of MessageQueue instances
        """
        query = cls.query.filter_by(status='pending')
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        # Get messages that are scheduled for now or in the past
        now = datetime.utcnow()
        query = query.filter(
            (cls.scheduled_at.is_(None)) | (cls.scheduled_at <= now)
        )
        
        # Order by priority (highest first) and then by creation date (oldest first)
        query = query.order_by(cls.priority.desc(), cls.created_at.asc())
        
        return query.limit(limit).all()


class MessageStatus(db.Model):
    """Model for storing message status updates."""
    
    __tablename__ = 'message_status'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message_queue.id'), nullable=False)
    status = db.Column(db.String(32), nullable=False)  # pending, sent, delivered, read, failed
    external_id = db.Column(db.String(64), nullable=True)  # ID from WhatsApp
    error_message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with message queue
    message = db.relationship('MessageQueue', back_populates='status_updates')
    
    def __repr__(self):
        return f'<MessageStatus {self.message_id}:{self.status}>'
    
    def to_dict(self):
        """Convert status to dictionary for API responses."""
        return {
            'id': self.id,
            'message_id': self.message_id,
            'status': self.status,
            'external_id': self.external_id,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat()
        }