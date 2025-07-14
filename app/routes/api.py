"""API routes for handling API requests."""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.whatsapp_session import WhatsAppSession
from app import db

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/sessions/whatsapp', methods=['GET'])
@login_required
def get_whatsapp_sessions():
    """Get WhatsApp Web sessions for the current user.
    
    Returns:
        JSON response with WhatsApp Web sessions
    """
    try:
        # Get active sessions from database
        sessions = WhatsAppSession.get_active_sessions()
        
        # Convert to list of dictionaries
        session_list = [{
            'id': session.id,
            'name': session.name,
            'session_id': session.session_id,
            'status': session.status,
            'last_connected': session.last_connected.isoformat() if session.last_connected else None
        } for session in sessions]
        
        return jsonify({
            'success': True,
            'sessions': session_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500