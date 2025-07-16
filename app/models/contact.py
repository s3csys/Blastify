"""Contact model for storing recipient information."""

from datetime import datetime
from app import db

class ContactGroup:
    """Contact group class for managing contact groups."""
    
    def __init__(self, name, contact_count=0, created_at=None, updated_at=None):
        self.id = name  # Using name as ID since we don't have a separate group model
        self.name = name
        self.contact_count = contact_count
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    # Create a query property that mimics SQLAlchemy's query interface
    class QueryProxy:
        @staticmethod
        def all():
            """Query all contact groups."""
            from sqlalchemy import func
            from app import db
            
            # Get distinct groups and their counts
            groups_data = db.session.query(
                Contact.group.label('name'),
                func.count(Contact.id).label('contact_count')
            ).filter(Contact.group != None, Contact.group != '')\
            .group_by(Contact.group).all()
            
            # Convert to ContactGroup objects
            return [ContactGroup(name=group.name, contact_count=group.contact_count) for group in groups_data]
    
    # Create a class-level query attribute
    query = QueryProxy()

class Contact(db.Model):
    """Contact model for storing recipient information."""
    
    __tablename__ = 'contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    email = db.Column(db.String(120))
    group = db.Column(db.String(50), default='default')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Contact {self.id}: {self.name} ({self.phone})>'
    
    def to_dict(self):
        """Convert contact to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'group': self.group,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }