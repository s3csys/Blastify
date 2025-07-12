from datetime import datetime
from app import db

class ApiCredential(db.Model):
    """Model for storing API credentials."""
    
    __tablename__ = 'api_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(64), index=True, nullable=False)
    key_name = db.Column(db.String(64), nullable=False)
    key_value = db.Column(db.String(256), nullable=False)
    credential_name = db.Column(db.String(128), nullable=True)  # Add this column
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Create a unique constraint on the combination of service_name and key_name
    __table_args__ = (db.UniqueConstraint('service_name', 'key_name', 'credential_name', name='_service_key_name_uc'),)
    
    def __repr__(self):
        return f'<ApiCredential {self.service_name}:{self.key_name}>'
    
    @classmethod
    def get_credential(cls, service_name, key_name):
        """Get a credential value by service name and key name.
        
        Args:
            service_name: The name of the service (e.g., 'whatsapp', 'telegram')
            key_name: The name of the credential key
            
        Returns:
            The credential value or None if not found
        """
        credential = cls.query.filter_by(
            service_name=service_name,
            key_name=key_name,
            is_active=True
        ).first()
        
        return credential.key_value if credential else None
    
    @classmethod
    def set_credential(cls, service_name, key_name, key_value, credential_name=None):
        """Set a credential value by service name and key name.
        
        Args:
            service_name: The name of the service (e.g., 'whatsapp', 'telegram')
            key_name: The name of the credential key
            key_value: The value to store
            credential_name: Optional name to identify this credential set
            
        Returns:
            The ApiCredential instance
        """
        credential = cls.query.filter_by(
            service_name=service_name,
            key_name=key_name,
            credential_name=credential_name
        ).first()
        
        if credential:
            credential.key_value = key_value
            credential.updated_at = datetime.utcnow()
            credential.is_active = True
        else:
            credential = cls(
                service_name=service_name,
                key_name=key_name,
                key_value=key_value,
                credential_name=credential_name
            )
            db.session.add(credential)
        
        db.session.commit()
        return credential
    
    @classmethod
    def get_credential(cls, service_name, key_name, credential_name=None):
        """Get a credential value by service name and key name.
        
        Args:
            service_name: The name of the service (e.g., 'whatsapp', 'telegram')
            key_name: The name of the credential key
            credential_name: Optional name to identify this credential set
            
        Returns:
            The credential value or None if not found
        """
        query = cls.query.filter_by(
            service_name=service_name,
            key_name=key_name,
            is_active=True
        )
        
        if credential_name is not None:
            query = query.filter_by(credential_name=credential_name)
            
        credential = query.first()
        
        return credential.key_value if credential else None
    
    @classmethod
    def get_credential_sets(cls, service_name):
        """Get all credential sets for a service.
        
        This method returns a list of dictionaries, where each dictionary
        represents a complete set of credentials for a specific instance.
        
        Args:
            service_name: The name of the service (e.g., 'whatsapp', 'telegram')
            
        Returns:
            List of credential sets, each as a dictionary
        """
        # Get all unique credential names for the service
        credential_names = db.session.query(cls.credential_name).filter_by(
            service_name=service_name,
            is_active=True
        ).distinct().all()
        
        credential_sets = []
        
        for name_tuple in credential_names:
            name = name_tuple[0]
            
            if name is None:
                continue
                
            # For each credential name, find all related credentials
            credentials = {'name': name}
            
            # Get instance_id and api_token for this credential set
            instance_id = cls.get_credential(service_name, 'instance_id', name)
            api_token = cls.get_credential(service_name, 'api_token', name)
            
            if instance_id and api_token:
                credentials['instance_id'] = instance_id
                credentials['api_token'] = api_token
                credential_sets.append(credentials)
        
        return credential_sets

    @classmethod
    def delete_credential_set(cls, service_name, credential_name):
        """Delete a complete credential set by service name and credential name.
        
        Args:
            service_name: The name of the service (e.g., 'whatsapp', 'telegram')
            credential_name: The name identifying this credential set
            
        Returns:
            Boolean indicating success
        """
        try:
            # Find all credentials with this service and credential name
            credentials = cls.query.filter_by(
                service_name=service_name,
                credential_name=credential_name
            ).all()
            
            if not credentials:
                return False
                
            # Delete all matching credentials
            for credential in credentials:
                db.session.delete(credential)
                
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
