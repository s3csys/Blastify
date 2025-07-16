"""Models for message template categories."""

from datetime import datetime
from app import db

class MessageTemplateCategory(db.Model):
    """Model for storing message template categories."""
    
    __tablename__ = 'message_template_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship with templates
    templates = db.relationship('MessageTemplate', back_populates='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<MessageTemplateCategory {self.name}>'
    
    def to_dict(self):
        """Convert category to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'template_count': self.templates.count()
        }