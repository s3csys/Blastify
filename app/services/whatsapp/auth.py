"""WhatsApp authentication service."""

import logging
from typing import Dict, Any, List, Optional

from app import db
from app.models.whatsapp_session import WhatsAppSession
from app.services.whatsapp.client import WhatsAppClient

logger = logging.getLogger(__name__)

class WhatsAppAuth:
    """Service for WhatsApp authentication and session management."""
    
    @staticmethod
    def create_session(session_name: str) -> Dict[str, Any]:
        """Create a new WhatsApp session.
        
        Args:
            session_name: Name for the new session
            
        Returns:
            Dictionary with session creation status and session ID if successful
        """
        try:
            # Check if session with this name already exists
            existing_session = WhatsAppSession.get_session_by_name(session_name)
            if existing_session:
                return {
                    "status": "failed",
                    "error": f"Session with name '{session_name}' already exists"
                }
            
            # Create a new client (which will create a session)
            client = WhatsAppClient(session_name=session_name)
            
            # Return session info
            return {
                "status": "success",
                "message": "Session created successfully",
                "session_id": client.session_id,
                "session_name": session_name
            }
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    @staticmethod
    def connect_session(session_id: str, headless: bool = True) -> Dict[str, Any]:
        """Connect to WhatsApp Web using a session.
        
        Args:
            session_id: ID of the session to connect
            headless: Whether to run the browser in headless mode
            
        Returns:
            Dictionary with connection status and QR code if available
        """
        try:
            # Create client with existing session
            client = WhatsAppClient(session_id=session_id)
            
            # Connect to WhatsApp Web
            result = client.connect(headless=headless)
            
            return result
            
        except Exception as e:
            logger.error(f"Error connecting session: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    @staticmethod
    def get_session_qr(session_id: str) -> Dict[str, Any]:
        """Get the QR code for a WhatsApp session.
        
        Args:
            session_id: ID of the session to get QR code for
            
        Returns:
            Dictionary with QR code data or error
        """
        try:
            # Get session from database
            session = WhatsAppSession.get_session_by_id(session_id)
            if not session:
                return {
                    "status": "failed",
                    "error": f"Session with ID '{session_id}' not found"
                }
            
            # If session already has a QR code, return it
            if session.qr_code:
                return {
                    "status": "success",
                    "qr_code": session.qr_code
                }
            
            # If session is already connected, return error
            if session.status == "connected":
                return {
                    "status": "failed",
                    "error": "Session is already connected"
                }
            
            # Connect to get a new QR code
            return WhatsAppAuth.connect_session(session_id)
            
        except Exception as e:
            logger.error(f"Error getting session QR code: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    @staticmethod
    def get_session_status(session_id: str) -> Dict[str, Any]:
        """Get the status of a WhatsApp session.
        
        Args:
            session_id: ID of the session to check
            
        Returns:
            Dictionary with session status
        """
        try:
            # Get session from database
            session = WhatsAppSession.get_session_by_id(session_id)
            if not session:
                return {
                    "status": "failed",
                    "error": f"Session with ID '{session_id}' not found"
                }
            
            # Return session info
            return {
                "status": "success",
                "session": session.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    @staticmethod
    def get_all_sessions() -> Dict[str, Any]:
        """Get all WhatsApp sessions.
        
        Returns:
            Dictionary with all sessions
        """
        try:
            # Get all active sessions
            sessions = WhatsAppSession.get_active_sessions()
            
            # Convert to dictionaries
            session_dicts = [session.to_dict() for session in sessions]
            
            return {
                "status": "success",
                "sessions": session_dicts
            }
            
        except Exception as e:
            logger.error(f"Error getting all sessions: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    @staticmethod
    def refresh_qr_code(session_id: str) -> Dict[str, Any]:
        """Refresh the QR code for a session.
        
        Args:
            session_id: ID of the session to refresh QR code for
            
        Returns:
            Dictionary with refresh status and new QR code if successful
        """
        try:
            # Create client with existing session
            client = WhatsAppClient(session_id=session_id)
            
            # Refresh QR code
            result = client.refresh_qr_code()
            
            return result
            
        except Exception as e:
            logger.error(f"Error refreshing QR code: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    @staticmethod
    def disconnect_session(session_id: str) -> Dict[str, Any]:
        """Disconnect a WhatsApp session.
        
        Args:
            session_id: ID of the session to disconnect
            
        Returns:
            Dictionary with disconnect status
        """
        try:
            # Create client with existing session
            client = WhatsAppClient(session_id=session_id)
            
            # Disconnect
            result = client.disconnect()
            
            return result
            
        except Exception as e:
            logger.error(f"Error disconnecting session: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    @staticmethod
    def delete_session(session_id: str) -> Dict[str, Any]:
        """Delete a WhatsApp session.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            Dictionary with deletion status
        """
        try:
            # Get session from database
            session = WhatsAppSession.get_session_by_id(session_id)
            if not session:
                return {
                    "status": "failed",
                    "error": f"Session with ID '{session_id}' not found"
                }
            
            # Disconnect if connected
            if session.status == "connected":
                client = WhatsAppClient(session_id=session_id)
                client.disconnect()
            
            # Mark session as inactive (soft delete)
            session.is_active = False
            db.session.commit()
            
            return {
                "status": "success",
                "message": "Session deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }