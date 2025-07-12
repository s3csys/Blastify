"""WhatsApp API routes."""

import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify

from app import db
from app.models.whatsapp_session import WhatsAppSession
from app.models.message_queue import MessageQueue, MessageStatus
from app.services.whatsapp.auth import WhatsAppAuth
from app.services.whatsapp.message import WhatsAppMessageService
from app.utils.validators import validate_message_request_new

logger = logging.getLogger(__name__)

# Create blueprint
whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/api/whatsapp')


# Session management routes
@whatsapp_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """Get all WhatsApp sessions."""
    try:
        sessions = WhatsAppSession.query.all()
        return jsonify({
            'status': 'success',
            'sessions': [{
                'id': session.id,
                'session_id': session.session_id,
                'name': session.name,
                'status': session.status,
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                'is_active': session.is_active
            } for session in sessions]
        }), 200
    except Exception as e:
        logger.error(f"Error getting sessions: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@whatsapp_bp.route('/sessions', methods=['POST'])
def create_session():
    """Create a new WhatsApp session."""
    try:
        data = request.json
        name = data.get('name', 'Default Session')
        
        result = WhatsAppAuth.create_session(name)
        
        if result.get('status') == 'success':
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@whatsapp_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a WhatsApp session by ID."""
    try:
        session = WhatsAppSession.get_session_by_id(session_id)
        
        if not session:
            return jsonify({
                'status': 'failed',
                'error': f"Session with ID '{session_id}' not found"
            }), 404
        
        return jsonify({
            'status': 'success',
            'session': {
                'id': session.id,
                'session_id': session.session_id,
                'name': session.name,
                'status': session.status,
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                'is_active': session.is_active
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@whatsapp_bp.route('/sessions/<session_id>/qr', methods=['GET'])
def get_session_qr(session_id):
    """Get QR code for a WhatsApp session."""
    try:
        result = WhatsAppAuth.get_session_qr(session_id)
        
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error getting session QR: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@whatsapp_bp.route('/sessions/<session_id>/refresh', methods=['POST'])
def refresh_session(session_id):
    """Refresh a WhatsApp session."""
    try:
        result = WhatsAppAuth.refresh_session(session_id)
        
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error refreshing session: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@whatsapp_bp.route('/sessions/<session_id>/disconnect', methods=['POST'])
def disconnect_session(session_id):
    """Disconnect a WhatsApp session."""
    try:
        result = WhatsAppAuth.disconnect_session(session_id)
        
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error disconnecting session: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@whatsapp_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a WhatsApp session."""
    try:
        result = WhatsAppAuth.delete_session(session_id)
        
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


# Messaging routes
@whatsapp_bp.route('/send', methods=['POST'])
def send_message():
    """Send a WhatsApp message."""
    try:
        data = request.json
        
        # Get session ID
        session_id = data.get('session_id')
        
        # Create message service
        message_service = WhatsAppMessageService(session_id=session_id)
        
        # Send message
        result = message_service.send_message(
            recipient=data.get('recipient'),
            message=data.get('message'),
            media_url=data.get('media_url')
        )
        
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@whatsapp_bp.route('/queue', methods=['POST'])
def queue_message():
    """Queue a WhatsApp message."""
    try:
        data = request.json
        
        # Get session ID
        session_id = data.get('session_id')
        
        # Create message service
        message_service = WhatsAppMessageService(session_id=session_id)
        
        # Queue message
        result = message_service.queue_message(
            recipient=data.get('recipient'),
            message=data.get('message'),
            media_url=data.get('media_url'),
            priority=data.get('priority', 0),
            scheduled_at=data.get('scheduled_at')
        )
        
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error queuing message: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@whatsapp_bp.route('/bulk', methods=['POST'])
def send_bulk_messages():
    """Send bulk WhatsApp messages."""
    try:
        data = request.json
        
        # Get session ID
        session_id = data.get('session_id')
        
        # Get messages
        messages = data.get('messages', [])
        if not messages:
            return jsonify({
                'status': 'failed',
                'error': 'No messages provided'
            }), 400
        
        # Validate messages
        valid_messages = []
        invalid_messages = []
        
        for msg in messages:
            validation = validate_message_request_new({
                '_use_new_format': True,
                'recipient': msg.get('recipient'),
                'message': msg.get('message'),
                'media_url': msg.get('media_url')
            })
            
            if validation.get('status') == 'success':
                valid_messages.append(msg)
            else:
                invalid_messages.append({
                    'message': msg,
                    'error': validation.get('error')
                })
        
        if not valid_messages:
            return jsonify({
                'status': 'failed',
                'error': 'No valid messages provided',
                'invalid_messages': invalid_messages
            }), 400
        
        # Get rate limit
        rate_limit_ms = data.get('rate_limit_ms', 200)
        
        # Queue task
        task = send_bulk_messages_task.delay(
            session_id=session_id,
            messages=valid_messages,
            rate_limit_ms=rate_limit_ms
        )
        
        return jsonify({
            'status': 'success',
            'message': f"Bulk send task queued with {len(valid_messages)} messages",
            'task_id': task.id,
            'valid_count': len(valid_messages),
            'invalid_count': len(invalid_messages),
            'invalid_messages': invalid_messages
        }), 200
    except Exception as e:
        logger.error(f"Error sending bulk messages: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@whatsapp_bp.route('/messages/<message_id>/status', methods=['GET'])
def get_message_status(message_id):
    """Get status of a WhatsApp message."""
    try:
        # Get message
        message = MessageQueue.query.get(message_id)
        if not message:
            return jsonify({
                'status': 'failed',
                'error': f"Message with ID '{message_id}' not found"
            }), 404
        
        # Get latest status
        status = MessageStatus.query.filter_by(message_id=message_id).order_by(MessageStatus.created_at.desc()).first()
        
        return jsonify({
            'status': 'success',
            'message': {
                'id': message.id,
                'recipient': message.recipient,
                'message': message.message,
                'media_url': message.media_url,
                'status': message.status,
                'created_at': message.created_at.isoformat() if message.created_at else None,
                'updated_at': message.updated_at.isoformat() if message.updated_at else None,
                'latest_status': {
                    'status': status.status,
                    'external_id': status.external_id,
                    'error_message': status.error_message,
                    'created_at': status.created_at.isoformat() if status.created_at else None
                } if status else None
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting message status: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


# Move this import to the end of the file to avoid circular imports
# from app.tasks.whatsapp_tasks import send_bulk_messages_task

# Bulk messaging route
@whatsapp_bp.route('/send-bulk', methods=['POST'])
def send_bulk_messages_async():  # Renamed from send_bulk_messages to send_bulk_messages_async
    """Send bulk messages asynchronously."""
    try:
        # Get request data
        data = request.get_json()
        
        # Validate request
        if not data or 'messages' not in data:
            return jsonify({
                'status': 'failed',
                'error': 'No messages provided'
            }), 400
        
        # Get session ID
        session_id = data.get('session_id')
        
        # Queue the task
        task = send_bulk_messages_task.delay(session_id, data['messages'])
        
        return jsonify({
            'status': 'success',
            'task_id': task.id,
            'message': f"Queued {len(data['messages'])} messages for sending"
        }), 202
        
    except Exception as e:
        logger.error(f"Error queuing bulk messages: {str(e)}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500

# Import the task at the end to avoid circular imports
from app.tasks.whatsapp_tasks import send_bulk_messages_task