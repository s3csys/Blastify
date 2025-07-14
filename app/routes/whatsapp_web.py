import logging
import uuid
import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.whatsapp_session import WhatsAppSession
from app.models.settings import Settings
from app import db

# Create blueprint for web routes
bp = Blueprint('whatsapp_web', __name__, url_prefix='/whatsapp')

@bp.route('/', methods=['GET'])
@login_required
def index():
    """Display WhatsApp sessions.
    
    Returns:
        Rendered template with WhatsApp sessions
    """
    sessions = WhatsAppSession.query.all()
    return render_template('whatsapp/index.html', sessions=sessions)

@bp.route('/connect', methods=['GET'])
@login_required
def connect():
    """Display WhatsApp connection page.
    
    Returns:
        Rendered template for connecting to WhatsApp
    """
    return render_template('whatsapp/connect.html')

@bp.route('/settings', methods=['GET'])
@login_required
def settings():
    """Display WhatsApp settings page.
    
    Returns:
        Rendered template with WhatsApp settings
    """
    # Get user's WhatsApp settings
    whatsapp_settings = Settings.get_settings_by_type(current_user.id, 'whatsapp')
    
    # If no settings exist yet, use defaults
    if not whatsapp_settings:
        whatsapp_settings = {
            'enable_rich_text': 'true',
            'enable_read_receipts': 'true',
            'message_retention': '30',
            'default_country_code': '+1',
            'enable_auto_replies': 'false',
            'notification_email': current_user.email
        }
    
    # Get auto-replies
    auto_replies = []
    auto_replies_json = Settings.get_setting(current_user.id, 'whatsapp', 'auto_replies', '{}')
    try:
        auto_replies_dict = json.loads(auto_replies_json)
        auto_replies = list(auto_replies_dict.values())
    except Exception as e:
        logging.error(f"Error parsing auto-replies: {str(e)}")
    
    return render_template('whatsapp/settings.html', settings=whatsapp_settings, auto_replies=auto_replies)

@bp.route('/connect_device', methods=['POST'])
@login_required
def connect_device():
    """Process WhatsApp device connection request.
    
    Returns:
        Redirect to WhatsApp index page or back to connect page with error
    """
    device_name = request.form.get('device_name')
    session_name = request.form.get('session_name')
    
    if not device_name or not session_name:
        flash('Please provide both device name and session', 'danger')
        return redirect(url_for('whatsapp_web.connect'))
    
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Create new WhatsApp session
        session = WhatsAppSession(
            name=device_name,
            credential=session_name,
            user_id=current_user.id,
            session_id=session_id,
            status='connecting'
        )
        db.session.add(session)
        db.session.commit()
        
        # Generate QR code or initiate connection process here
        # This would typically be handled by a background task
        
        flash('WhatsApp device connection initiated. Please scan the QR code when it appears.', 'success')
        return redirect(url_for('whatsapp_web.index'))
    except Exception as e:
        logging.error(f"Error connecting WhatsApp device: {str(e)}")
        flash(f'Error connecting WhatsApp device: {str(e)}', 'danger')
        return redirect(url_for('whatsapp_web.connect'))

@bp.route('/check-connection-status/<session_id>', methods=['GET'])
@login_required
def check_connection_status(session_id):
    """Check the connection status of a WhatsApp session.
    
    Args:
        session_id: The session ID to check
        
    Returns:
        JSON response with connection status
    """
    try:
        session = WhatsAppSession.query.filter_by(session_id=session_id).first()
        
        if not session:
            return jsonify({
                'connected': False,
                'error': 'Session not found'
            })
        
        if session.status == 'connected':
            return jsonify({
                'connected': True
            })
        elif session.status == 'error':
            return jsonify({
                'connected': False,
                'error': 'Connection failed'
            })
        else:
            return jsonify({
                'connected': False
            })
    except Exception as e:
        logging.error(f"Error checking connection status: {str(e)}")
        return jsonify({
            'connected': False,
            'error': str(e)
        })

@bp.route('/generate-qr', methods=['GET'])
@login_required
def generate_qr_page():
    """Display the QR code generation page.
    
    Returns:
        Rendered template for generating WhatsApp QR code
    """
    return render_template('whatsapp/generate_qr.html')

@bp.route('/generate-qr-code', methods=['POST'])
@login_required
def generate_qr_code():
    """Generate a QR code for WhatsApp connection.
    
    Returns:
        JSON response with QR code data
    """
    try:
        device_name = request.form.get('device_name')
        
        if not device_name:
            return jsonify({
                'success': False,
                'error': 'Please provide a device name'
            })
        
        # Create a new WhatsApp session using WhatsAppAuth
        from app.services.whatsapp.auth import WhatsAppAuth
        
        # Create the session
        create_result = WhatsAppAuth.create_session(device_name)
        
        if create_result.get('status') != 'success':
            return jsonify({
                'success': False,
                'error': create_result.get('error', 'Failed to create WhatsApp session')
            })
        
        session_id = create_result.get('session_id')
        
        # Get the QR code for the session
        qr_result = WhatsAppAuth.get_session_qr(session_id)
        
        if qr_result.get('status') != 'success':
            return jsonify({
                'success': False,
                'error': qr_result.get('error', 'Failed to generate QR code')
            })
        
        # Update the session with user ID
        session = WhatsAppSession.get_session_by_id(session_id)
        if session:
            session.user_id = current_user.id
            db.session.commit()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'qr_code': qr_result.get('qr_code')
        })
    except Exception as e:
        logging.error(f"Error generating QR code: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })
    except Exception as e:
        logging.error(f"Error generating QR code: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    """Update WhatsApp settings.
    
    Returns:
        Redirect to settings page with success/error message
    """
    try:
        settings_type = request.form.get('settings_type', 'whatsapp')
        
        # Process form data based on settings type
        if settings_type == 'general':
            # Update general WhatsApp settings
            enable_rich_text = 'true' if request.form.get('enable_rich_text') else 'false'
            enable_read_receipts = 'true' if request.form.get('enable_read_receipts') else 'false'
            message_retention = request.form.get('message_retention', '30')
            default_reply_timeout = request.form.get('default_reply_timeout', '24')
            
            # Save settings to database
            Settings.set_setting(current_user.id, 'whatsapp', 'enable_rich_text', enable_rich_text)
            Settings.set_setting(current_user.id, 'whatsapp', 'enable_read_receipts', enable_read_receipts)
            Settings.set_setting(current_user.id, 'whatsapp', 'message_retention', message_retention)
            Settings.set_setting(current_user.id, 'whatsapp', 'default_reply_timeout', default_reply_timeout)
            
        elif settings_type == 'notification':
            # Update notification settings
            notify_new_messages = 'true' if request.form.get('notify_new_messages') else 'false'
            notify_delivery_failures = 'true' if request.form.get('notify_delivery_failures') else 'false'
            notify_session_expiry = 'true' if request.form.get('notify_session_expiry') else 'false'
            notification_email = request.form.get('notification_email', '')
            enable_in_app_notifications = 'true' if request.form.get('enable_in_app_notifications') else 'false'
            quiet_hours_start = request.form.get('quiet_hours_start', '22:00')
            quiet_hours_end = request.form.get('quiet_hours_end', '07:00')
            
            # Save settings to database
            Settings.set_setting(current_user.id, 'whatsapp', 'notify_new_messages', notify_new_messages)
            Settings.set_setting(current_user.id, 'whatsapp', 'notify_delivery_failures', notify_delivery_failures)
            Settings.set_setting(current_user.id, 'whatsapp', 'notify_session_expiry', notify_session_expiry)
            Settings.set_setting(current_user.id, 'whatsapp', 'notification_email', notification_email)
            Settings.set_setting(current_user.id, 'whatsapp', 'enable_in_app_notifications', enable_in_app_notifications)
            Settings.set_setting(current_user.id, 'whatsapp', 'quiet_hours_start', quiet_hours_start)
            Settings.set_setting(current_user.id, 'whatsapp', 'quiet_hours_end', quiet_hours_end)
            
        elif settings_type == 'auto_reply':
            # Update auto-reply settings
            enable_auto_replies = 'true' if request.form.get('enable_auto_replies') else 'false'
            
            # Save settings to database
            Settings.set_setting(current_user.id, 'whatsapp', 'enable_auto_replies', enable_auto_replies)
        
        flash('Settings updated successfully', 'success')
        return redirect(url_for('whatsapp_web.settings'))
    except Exception as e:
        logging.error(f"Error updating settings: {str(e)}")
        flash(f'Error updating settings: {str(e)}', 'danger')
        return redirect(url_for('whatsapp_web.settings'))

@bp.route('/add_auto_reply', methods=['POST'])
@login_required
def add_auto_reply():
    """Add a new auto-reply rule.
    
    Returns:
        Redirect to settings page with success/error message
    """
    try:
        name = request.form.get('name')
        trigger_type = request.form.get('trigger_type')
        response = request.form.get('response')
        is_active = 'true' if request.form.get('is_active') else 'false'
        
        if not name or not trigger_type or not response:
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('whatsapp_web.settings'))
        
        # Create a unique ID for this auto-reply
        auto_reply_id = str(uuid.uuid4())
        
        # Get existing auto-replies or initialize empty list
        auto_replies_json = Settings.get_setting(current_user.id, 'whatsapp', 'auto_replies', '{}')
        try:
            auto_replies = json.loads(auto_replies_json)
        except:
            auto_replies = {}
        
        # Create new auto-reply entry
        auto_reply = {
            'id': auto_reply_id,
            'name': name,
            'trigger_type': trigger_type,
            'response': response,
            'is_active': is_active == 'true',
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Add trigger-specific fields
        if trigger_type == 'keyword':
            trigger_keyword = request.form.get('trigger_keyword', '')
            if not trigger_keyword:
                flash('Please provide trigger keywords', 'danger')
                return redirect(url_for('whatsapp_web.settings'))
            auto_reply['trigger_keyword'] = trigger_keyword
        elif trigger_type == 'away':
            away_timeout = request.form.get('away_timeout', '24')
            auto_reply['away_timeout'] = away_timeout
        
        # Add to auto-replies collection
        auto_replies[auto_reply_id] = auto_reply
        
        # Save updated auto-replies
        Settings.set_setting(current_user.id, 'whatsapp', 'auto_replies', json.dumps(auto_replies))
        
        flash('Auto-reply added successfully', 'success')
        return redirect(url_for('whatsapp_web.settings'))
    except Exception as e:
        logging.error(f"Error adding auto-reply: {str(e)}")
        flash(f'Error adding auto-reply: {str(e)}', 'danger')
        return redirect(url_for('whatsapp_web.settings'))

@bp.route('/update_auto_reply/<reply_id>', methods=['POST'])
@login_required
def update_auto_reply(reply_id):
    """Update an existing auto-reply rule.
    
    Args:
        reply_id: The ID of the auto-reply to update
        
    Returns:
        Redirect to settings page with success/error message
    """
    try:
        name = request.form.get('name')
        response = request.form.get('response')
        is_active = 'true' if request.form.get('is_active') else 'false'
        
        if not name or not response:
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('whatsapp_web.settings'))
        
        # Get existing auto-replies
        auto_replies_json = Settings.get_setting(current_user.id, 'whatsapp', 'auto_replies', '{}')
        try:
            auto_replies = json.loads(auto_replies_json)
        except:
            auto_replies = {}
        
        # Check if auto-reply exists
        if reply_id not in auto_replies:
            flash('Auto-reply not found', 'danger')
            return redirect(url_for('whatsapp_web.settings'))
        
        # Update auto-reply
        auto_reply = auto_replies[reply_id]
        auto_reply['name'] = name
        auto_reply['response'] = response
        auto_reply['is_active'] = is_active == 'true'
        auto_reply['updated_at'] = datetime.utcnow().isoformat()
        
        # Update trigger-specific fields
        trigger_type = auto_reply['trigger_type']
        if trigger_type == 'keyword':
            trigger_keyword = request.form.get('trigger_keyword', '')
            if not trigger_keyword:
                flash('Please provide trigger keywords', 'danger')
                return redirect(url_for('whatsapp_web.settings'))
            auto_reply['trigger_keyword'] = trigger_keyword
        elif trigger_type == 'away':
            away_timeout = request.form.get('away_timeout', '24')
            auto_reply['away_timeout'] = away_timeout
        
        # Save updated auto-replies
        Settings.set_setting(current_user.id, 'whatsapp', 'auto_replies', json.dumps(auto_replies))
        
        flash('Auto-reply updated successfully', 'success')
        return redirect(url_for('whatsapp_web.settings'))
    except Exception as e:
        logging.error(f"Error updating auto-reply: {str(e)}")
        flash(f'Error updating auto-reply: {str(e)}', 'danger')
        return redirect(url_for('whatsapp_web.settings'))

@bp.route('/delete_auto_reply/<reply_id>', methods=['POST'])
@login_required
def delete_auto_reply(reply_id):
    """Delete an existing auto-reply rule.
    
    Args:
        reply_id: The ID of the auto-reply to delete
        
    Returns:
        Redirect to settings page with success/error message
    """
    try:
        # Get existing auto-replies
        auto_replies_json = Settings.get_setting(current_user.id, 'whatsapp', 'auto_replies', '{}')
        try:
            auto_replies = json.loads(auto_replies_json)
        except:
            auto_replies = {}
        
        # Check if auto-reply exists
        if reply_id not in auto_replies:
            flash('Auto-reply not found', 'danger')
            return redirect(url_for('whatsapp_web.settings'))
        
        # Delete auto-reply
        del auto_replies[reply_id]
        
        # Save updated auto-replies
        Settings.set_setting(current_user.id, 'whatsapp', 'auto_replies', json.dumps(auto_replies))
        
        flash('Auto-reply deleted successfully', 'success')
        return redirect(url_for('whatsapp_web.settings'))
    except Exception as e:
        logging.error(f"Error deleting auto-reply: {str(e)}")
        flash(f'Error deleting auto-reply: {str(e)}', 'danger')
        return redirect(url_for('whatsapp_web.settings'))

@bp.route('/toggle-auto-reply-status/<reply_id>/<int:new_status>', methods=['POST'])
@login_required
def toggle_auto_reply_status(reply_id, new_status):
    """Toggle the active status of an auto-reply rule.
    
    Args:
        reply_id: The ID of the auto-reply to update
        new_status: The new status (1 for active, 0 for inactive)
        
    Returns:
        JSON response with success/error message
    """
    try:
        # Get existing auto-replies
        auto_replies_json = Settings.get_setting(current_user.id, 'whatsapp', 'auto_replies', '{}')
        try:
            auto_replies = json.loads(auto_replies_json)
        except:
            auto_replies = {}
        
        # Check if auto-reply exists
        if reply_id not in auto_replies:
            return jsonify({'success': False, 'error': 'Auto-reply not found'})
        
        # Update status
        auto_replies[reply_id]['is_active'] = new_status == 1
        auto_replies[reply_id]['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated auto-replies
        Settings.set_setting(current_user.id, 'whatsapp', 'auto_replies', json.dumps(auto_replies))
        
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error toggling auto-reply status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/refresh_session/<session_id>', methods=['POST'])
@login_required
def refresh_session(session_id):
    """Refresh a WhatsApp session.
    
    Args:
        session_id: The ID of the session to refresh
        
    Returns:
        Redirect to WhatsApp index page with success/error message
    """
    try:
        # Use the WhatsAppAuth service to refresh the session
        from app.services.whatsapp.auth import WhatsAppAuth
        
        result = WhatsAppAuth.refresh_session(session_id)
        
        if result.get('status') == 'success':
            flash('WhatsApp session refreshed successfully', 'success')
        else:
            flash(f'Error refreshing WhatsApp session: {result.get("error", "Unknown error")}', 'danger')
            
        return redirect(url_for('whatsapp_web.index'))
    except Exception as e:
        logging.error(f"Error refreshing WhatsApp session: {str(e)}")
        flash(f'Error refreshing WhatsApp session: {str(e)}', 'danger')
        return redirect(url_for('whatsapp_web.index'))


@bp.route('/disconnect/<session_id>', methods=['POST'])
@login_required
def disconnect(session_id):
    """Disconnect a WhatsApp session.
    
    Args:
        session_id: The ID of the session to disconnect
        
    Returns:
        Redirect to WhatsApp index page with success/error message
    """
    try:
        # Get the session
        session = WhatsAppSession.query.filter_by(session_id=session_id).first()
        
        if not session:
            flash('WhatsApp session not found', 'danger')
            return redirect(url_for('whatsapp_web.index'))
        
        # Use the WhatsAppAuth service to disconnect the session
        from app.services.whatsapp.auth import WhatsAppAuth
        
        result = WhatsAppAuth.disconnect_session(session_id)
        
        if result.get('status') == 'success':
            # Update session status in database
            session.status = 'disconnected'
            session.is_active = False
            db.session.commit()
            
            flash('WhatsApp session disconnected successfully', 'success')
        else:
            flash(f'Error disconnecting WhatsApp session: {result.get("error", "Unknown error")}', 'danger')
            
        return redirect(url_for('whatsapp_web.index'))
    except Exception as e:
        logging.error(f"Error disconnecting WhatsApp session: {str(e)}")
        flash(f'Error disconnecting WhatsApp session: {str(e)}', 'danger')
        return redirect(url_for('whatsapp_web.index'))