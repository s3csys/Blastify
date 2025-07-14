"""WhatsApp bulk messaging routes."""

import logging
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.models.whatsapp_session import WhatsAppSession
from app.models.message_queue import MessageQueue, MessageStatus
from app.services.whatsapp.bulk_messenger import WhatsAppBulkMessenger

logger = logging.getLogger(__name__)

# Create blueprint for bulk messaging routes
bp = Blueprint('whatsapp_bulk', __name__, url_prefix='/whatsapp/bulk')

@bp.route('/', methods=['GET'])
@login_required
def index():
    """Display bulk messaging interface.
    
    Returns:
        Rendered template for bulk messaging
    """
    # Get active WhatsApp sessions
    sessions = WhatsAppSession.query.filter_by(status="connected").all()
    
    # Get recent message queues
    recent_queues = MessageQueue.query.order_by(MessageQueue.created_at.desc()).limit(10).all()
    
    return render_template('whatsapp/bulk.html', sessions=sessions, recent_queues=recent_queues)

@bp.route('/send', methods=['POST'])
@login_required
def send_bulk_messages():
    """Send bulk messages to multiple recipients.
    
    Returns:
        JSON response with send status
    """
    try:
        # Get request data
        session_id = request.form.get('session_id')
        message = request.form.get('message')
        media_url = request.form.get('media_url')
        recipients_raw = request.form.get('recipients', '')
        
        # Process recipients (split by newline, comma, or semicolon)
        recipients = [r.strip() for r in recipients_raw.replace('\n', ',').replace(';', ',').split(',') if r.strip()]
        
        # Validate input
        if not recipients:
            return jsonify({
                'success': False,
                'error': 'No recipients provided'
            }), 400
        
        if not message and not media_url:
            return jsonify({
                'success': False,
                'error': 'Either message or media URL must be provided'
            }), 400
        
        # Create bulk messenger service
        bulk_messenger = WhatsAppBulkMessenger(session_id=session_id)
        
        # Send messages
        result = bulk_messenger.send_bulk_messages(recipients, message, media_url)
        
        if result.get('status') == 'success':
            return jsonify({
                'success': True,
                'message': result.get('message'),
                'success_count': result.get('success_count'),
                'failed_count': result.get('failed_count'),
                'results': result.get('results')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error')
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending bulk messages: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/queue', methods=['POST'])
@login_required
def queue_bulk_messages():
    """Queue bulk messages to be sent later.
    
    Returns:
        JSON response with queue status
    """
    try:
        # Get request data
        session_id = request.form.get('session_id')
        message = request.form.get('message')
        media_url = request.form.get('media_url')
        recipients_raw = request.form.get('recipients', '')
        priority = int(request.form.get('priority', '0'))
        scheduled_at = request.form.get('scheduled_at')
        
        # Process recipients (split by newline, comma, or semicolon)
        recipients = [r.strip() for r in recipients_raw.replace('\n', ',').replace(';', ',').split(',') if r.strip()]
        
        # Validate input
        if not recipients:
            return jsonify({
                'success': False,
                'error': 'No recipients provided'
            }), 400
        
        if not message and not media_url:
            return jsonify({
                'success': False,
                'error': 'Either message or media URL must be provided'
            }), 400
        
        # Create bulk messenger service
        bulk_messenger = WhatsAppBulkMessenger(session_id=session_id)
        
        # Queue messages
        result = bulk_messenger.queue_bulk_messages(
            recipients, message, media_url, priority, scheduled_at
        )
        
        if result.get('status') == 'success':
            return jsonify({
                'success': True,
                'message': result.get('message'),
                'success_count': result.get('success_count'),
                'failed_count': result.get('failed_count'),
                'failed_recipients': result.get('failed_recipients')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error')
            }), 500
            
    except Exception as e:
        logger.error(f"Error queuing bulk messages: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/process-queue', methods=['POST'])
@login_required
def process_queue():
    """Process the message queue.
    
    Returns:
        JSON response with processing status
    """
    try:
        # Get request data
        session_id = request.form.get('session_id')
        batch_size = int(request.form.get('batch_size', '50'))
        
        # Create bulk messenger service
        bulk_messenger = WhatsAppBulkMessenger(session_id=session_id)
        
        # Process queue
        result = bulk_messenger.process_queue(batch_size=batch_size)
        
        if result.get('status') == 'success':
            return jsonify({
                'success': True,
                'message': result.get('message'),
                'processed_count': result.get('processed_count'),
                'success_count': result.get('success_count'),
                'failed_count': result.get('failed_count')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error')
            }), 500
            
    except Exception as e:
        logger.error(f"Error processing message queue: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/queue-status', methods=['GET'])
@login_required
def queue_status():
    """Get status of the message queue.
    
    Returns:
        JSON response with queue status
    """
    try:
        # Get counts by status
        pending_count = MessageQueue.query.filter_by(status="pending").count()
        processing_count = MessageQueue.query.filter_by(status="processing").count()
        sent_count = MessageQueue.query.filter_by(status="sent").count()
        failed_count = MessageQueue.query.filter_by(status="failed").count()
        
        # Get recent messages
        recent_messages = MessageQueue.query.order_by(MessageQueue.created_at.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'queue_status': {
                'pending': pending_count,
                'processing': processing_count,
                'sent': sent_count,
                'failed': failed_count,
                'total': pending_count + processing_count + sent_count + failed_count
            },
            'recent_messages': [{
                'id': msg.id,
                'recipient': msg.recipient,
                'status': msg.status,
                'created_at': msg.created_at.isoformat() if msg.created_at else None
            } for msg in recent_messages]
        })
            
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500