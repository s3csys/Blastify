"""Message routes for handling message sending operations."""
import os
import json  # Add this import
from flask import Blueprint, request, jsonify, current_app, session, redirect, url_for, render_template, flash
from flask_login import login_required, current_user  # Add this import
from flask import send_from_directory  # Add this import for templates_media route
from app.services.message_service import MessageService, WhatsAppService  # Added WhatsAppService import
from app.utils.validators import validate_message_request
from app.models.message import Message
from app.models.user import User
from app.models.whatsapp_session import WhatsAppSession  # Replace ApiCredential with WhatsAppSession
from app import db

bp = Blueprint('message', __name__)

@bp.route('/send', methods=['POST'])
def send_message():
    """Send a message to a single recipient.
    
    Returns:
        JSON response with status of the message send operation or redirect to message history
    """
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            # Handle form data
            recipient_type = request.form.get('recipient_type')
            message_content = request.form.get('content')
            
            # Determine recipient based on recipient type
            recipient = None
            if recipient_type == 'individual':
                # Get selected contacts
                individual_contacts = request.form.getlist('individual_contacts[]')
                if individual_contacts:
                    # For simplicity, use the first contact
                    recipient = individual_contacts[0]  # In a real app, you'd handle multiple recipients
            elif recipient_type == 'group':
                # Get selected group
                contact_group = request.form.get('contact_group')
                # Here you would fetch all contacts in this group
                # For now, just use the group ID as a placeholder
                recipient = f"group:{contact_group}"
            elif recipient_type == 'custom':
                # Get custom numbers
                custom_numbers = request.form.get('custom_numbers')
                if custom_numbers:
                    # Split by comma and use first number
                    numbers = [num.strip() for num in custom_numbers.split(',')]
                    if numbers:
                        recipient = numbers[0]  # In a real app, you'd handle multiple recipients
            
            data = {
                'platform': request.form.get('platform', 'whatsapp'),
                'recipient': recipient,
                'message': message_content,
                'media_url': None  # Handle file upload separately
            }
            
            # Handle file upload if present
            if 'media' in request.files and request.files['media'].filename:
                # Save the file and get the URL
                # This is a placeholder - implement file storage logic
                file = request.files['media']
                # Example: file.save(os.path.join(upload_folder, file.filename))
                data['media_url'] = f"/uploads/{file.filename}"
        
        # Validate request data
        if request.is_json:
            errors = validate_message_request(data)
            if errors:
                return jsonify({'success': False, 'errors': errors}), 400
        else:
            # Basic validation for form data
            errors = []
            if not data.get('recipient'):
                errors.append('Recipient is required')
            if not data.get('message'):
                errors.append('Message content is required')
                
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('message.compose'))
        
        # Create message service based on platform
        platform = data.get('platform', 'whatsapp').lower()
        message_service = MessageService.create(platform)
        
        # Send message
        result = message_service.send_message(
            recipient=data['recipient'],
            message=data['message'],
            media_url=data.get('media_url')
        )
        
        # Save to database
        message = Message(
            platform=platform,
            recipient=data['recipient'],
            message_text=data['message'],
            media_url=data.get('media_url'),
            status=result['status']
        )
        db.session.add(message)
        db.session.commit()
        
        # Return JSON or redirect based on request type
        if request.is_json:
            return jsonify({
                'success': True,
                'message_id': message.id,
                'status': result['status']
            })
        else:
            flash('Message sent successfully!', 'success')
            return redirect(url_for('message.index'))
        
    except Exception as e:
        current_app.logger.error(f"Error sending message: {str(e)}")
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Failed to send message',
                'details': str(e)
            }), 500
        else:
            flash(f'Failed to send message: {str(e)}', 'danger')
            return redirect(url_for('message.compose'))

@bp.route('/bulk/send', methods=['POST'])
def send_bulk_messages():
    """Send messages to multiple recipients asynchronously.
    
    Returns:
        JSON response with bulk operation ID
    """
    try:
        data = request.get_json()
        
        # Validate request data
        if 'messages' not in data or not isinstance(data['messages'], list):
            return jsonify({
                'success': False,
                'error': 'Messages list is required'
            }), 400
            
        platform = data.get('platform', 'whatsapp').lower()
        
        # Queue bulk messages for async processing
        from app.tasks.message_tasks import send_bulk_messages_task
        task = send_bulk_messages_task.delay(
            platform=platform,
            messages=data['messages']
        )
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': f'Bulk send operation queued with {len(data["messages"])} messages'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error queuing bulk messages: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to queue bulk messages',
            'details': str(e)
        }), 500

@bp.route('/bulk/status/<task_id>', methods=['GET'])
def get_bulk_status(task_id):
    """Get the status of a bulk message operation.
    
    Args:
        task_id: The ID of the bulk operation task
        
    Returns:
        JSON response with task status
    """
    try:
        from app.tasks.message_tasks import send_bulk_messages_task
        task = send_bulk_messages_task.AsyncResult(task_id)
        
        response = {
            'task_id': task_id,
            'status': task.status,
        }
        
        if task.status == 'SUCCESS':
            response['result'] = task.result
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error checking task status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to check task status',
            'details': str(e)
        }), 500


@bp.route('/connect-messaging', methods=['GET', 'POST'])
@login_required
def connect_messaging():
    """Connect to WhatsApp or Telegram messaging services."""
    user = current_user
    if not user:
        return redirect(url_for('auth.login'))
    
    # Initialize variables
    whatsapp_connected = False
    telegram_connected = False
    
    # Create WhatsApp service
    whatsapp_service = WhatsAppService()
    
    # Get available WhatsApp sessions
    whatsapp_sessions = whatsapp_service.get_all_sessions()
    
    # Check actual WhatsApp connection status
    try:
        whatsapp_connected = whatsapp_service.is_connected()
    except Exception as e:
        current_app.logger.error(f"Error checking WhatsApp connection: {str(e)}")
    
    # Handle connection requests
    if request.method == 'POST':
        service = request.form.get('service')
        
        if service == 'whatsapp':
            try:
                # Get session name from form if provided
                session_name = request.form.get('session_name')
                
                # If no session name provided, generate one
                if not session_name:
                    import uuid
                    session_name = f"WhatsApp-{str(uuid.uuid4())[:8]}"
                
                # Create a new WhatsApp session
                result = whatsapp_service.create_session(session_name, user_id=user.id)
                
                if result.get('status') == 'success':
                    flash(f"WhatsApp session '{session_name}' created. Scan the QR code to connect.", "success")
                    
                    # Generate QR code
                    qr_code = whatsapp_service.generate_qr_code(result.get('session_id'))
                    if qr_code:
                        # Store QR code in session for display
                        session['whatsapp_qr_code'] = qr_code
                        session['whatsapp_session_id'] = result.get('session_id')
                    else:
                        flash("Failed to generate QR code. Please try again.", "warning")
                else:
                    flash(f"Failed to create WhatsApp session: {result.get('message', 'Unknown error')}", "error")
                
            except Exception as e:
                current_app.logger.error(f"Error connecting to WhatsApp: {str(e)}")
                flash(f"Error connecting to WhatsApp: {str(e)}", "error")
        
        elif service == 'telegram':
            # Similar implementation for Telegram
            pass
    
    return render_template('connect_messaging.html', 
                          whatsapp_connected=whatsapp_connected,
                          telegram_connected=telegram_connected,
                          whatsapp_sessions=whatsapp_sessions,
                          user=user)


@bp.route('/disconnect-service/<service>', methods=['POST'])
@login_required
def disconnect_service(service):
    """Disconnect from a messaging service.
    
    Args:
        service: The service to disconnect from (whatsapp, telegram)
        
    Returns:
        Redirect to the connect messaging page
    """
    
    try:
        if service == 'whatsapp':
            # Implement WhatsApp disconnection logic for WhatsApp Web
            try:
                # Create WhatsApp service
                whatsapp_service = WhatsAppService()
                
                # Get all active sessions
                sessions = whatsapp_service.get_all_sessions()
                
                # Disconnect all sessions
                from app.services.whatsapp.client import WhatsAppClient
                for session in sessions:
                    try:
                        # Close the browser session
                        client = WhatsAppClient(session_id=session.session_id)
                        client.disconnect()
                        
                        # Update session status
                        session.status = "disconnected"
                        db.session.commit()
                    except Exception as session_error:
                        current_app.logger.error(f"Error disconnecting session {session.session_id}: {str(session_error)}")
                
                # Verify disconnection
                if not whatsapp_service.is_connected():
                    flash("Successfully disconnected from WhatsApp", "success")
                else:
                    flash("Failed to disconnect from WhatsApp. Please try again.", "error")
            except Exception as e:
                current_app.logger.error(f"Error during WhatsApp logout: {str(e)}")
                flash(f"Error disconnecting from WhatsApp: {str(e)}", "error")
        
        elif service == 'telegram':
            # Implement Telegram disconnection logic here
            flash("Successfully disconnected from Telegram", "success")
        
        else:
            flash(f"Unknown service: {service}", "error")
    
    except Exception as e:
        current_app.logger.error(f"Error disconnecting from {service}: {str(e)}")
        flash(f"Error disconnecting from {service}: {str(e)}", "error")
    
    return redirect(url_for('message.connect_messaging'))


@bp.route('/clear-whatsapp-flag', methods=['GET'])
def clear_whatsapp_flag():
    """Clear the WhatsApp Web flag from the session."""
    if 'open_whatsapp_web' in session:
        session.pop('open_whatsapp_web')
    return jsonify({'success': True})


@bp.route('/manage-sessions', methods=['POST'])
@login_required
def manage_sessions():
    """Manage WhatsApp sessions (create, delete, connect).
    
    Returns:
        Redirect to the connect messaging page
    """
    
    action = request.form.get('action')
    service = request.form.get('service')
    
    if service == 'whatsapp':
        whatsapp_service = WhatsAppService()
        
        if action == 'create':
            # Get form data
            session_name = request.form.get('session_name')
            
            if not session_name:
                # Generate a session name if not provided
                import uuid
                session_name = f"WhatsApp-{str(uuid.uuid4())[:8]}"
            
            # Create a new session
            user_id = current_user.id
            result = whatsapp_service.create_session(session_name, user_id=user_id)
            
            if result.get('status') == 'success':
                # Generate QR code
                qr_code = whatsapp_service.generate_qr_code(result.get('session_id'))
                if qr_code:
                    # Store QR code in session for display
                    session['whatsapp_qr_code'] = qr_code
                    session['whatsapp_session_id'] = result.get('session_id')
                    flash(f"Session '{session_name}' created successfully. Scan the QR code to connect.", "success")
                else:
                    flash("Session created but failed to generate QR code. Try connecting again.", "warning")
            else:
                flash(f"Failed to create session: {result.get('message', 'Unknown error')}", "error")
                    
        elif action == 'delete':
            session_name = request.form.get('session_name')
            
            if not session_name:
                flash("Session name is required", "error")
            else:
                # Delete session
                if whatsapp_service.delete_session(session_name):
                    flash(f"Session '{session_name}' deleted successfully", "success")
                else:
                    flash("Failed to delete session", "error")
                    
        elif action == 'connect':
            session_name = request.form.get('session_name')
            
            if not session_name:
                flash("Session name is required", "error")
            else:
                # Get session and generate QR code
                session_obj = whatsapp_service.get_session_by_name(session_name)
                if not session_obj:
                    flash(f"Session '{session_name}' not found", "error")
                else:
                    # Generate QR code
                    qr_code = whatsapp_service.generate_qr_code(session_obj.session_id)
                    if qr_code:
                        # Store QR code in session for display
                        session['whatsapp_qr_code'] = qr_code
                        session['whatsapp_session_id'] = session_obj.session_id
                        flash(f"Connecting to session '{session_name}'. Scan the QR code.", "success")
                    else:
                        flash("Failed to generate QR code. Try again.", "error")
    
    return redirect(url_for('message.connect_messaging'))


# Add these imports at the top if not already present
import base64
from flask import jsonify

# Add these new routes
@bp.route('/generate-whatsapp-qr', methods=['POST'])
@login_required
def generate_whatsapp_qr():
    """Generate a QR code for WhatsApp Web authentication.
    
    Returns:
        JSON response with QR code data
    """
    
    try:
        session_name = request.form.get('session_name')
        if not session_name:
            return jsonify({'success': False, 'error': 'Session name is required'}), 400
        
        # Create WhatsApp service with the selected session
        whatsapp_service = WhatsAppService(session_name)
        
        # Get session and generate QR code
        session_obj = whatsapp_service.get_session_by_name(session_name)
        if not session_obj:
            return jsonify({'success': False, 'error': f"Session '{session_name}' not found"}), 400
        
        # Generate QR code
        qr_code_base64 = whatsapp_service.generate_qr_code(session_obj.session_id)
        if not qr_code_base64:
            return jsonify({'success': False, 'error': 'Failed to generate QR code'}), 500
        
        return jsonify({
            'success': True,
            'qr_code': qr_code_base64
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating WhatsApp QR code: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/check-whatsapp-connection', methods=['POST'])
@login_required
def check_whatsapp_connection():
    """Check if WhatsApp is connected after QR code scan.
    
    Returns:
        JSON response with connection status
    """
    
    try:
        session_name = request.form.get('session_name')
        if not session_name:
            return jsonify({'success': False, 'error': 'Session name is required'}), 400
        
        # Create WhatsApp service with the selected session
        whatsapp_service = WhatsAppService(session_name)
        
        # Get session
        session_obj = whatsapp_service.get_session_by_name(session_name)
        if not session_obj:
            return jsonify({'success': False, 'error': f"Session '{session_name}' not found"}), 400
        
        # Check connection status
        connected = whatsapp_service.is_connected(session_obj.session_id)
        
        return jsonify({
            'success': True,
            'connected': connected
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking WhatsApp connection: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/', methods=['GET'])
@login_required  # Replace manual session check with decorator
def index():
    """Display all messages/message history.
    
    Returns:
        Rendered template with message history
    """
    # Get messages from database
    messages = Message.query.all()
    
    return render_template('messages/history.html', messages=messages)


# Add these routes to your message.py file

@bp.route('/compose', methods=['GET'])
@login_required
def compose():
    """Display message composition page.
    
    Returns:
        Rendered template for composing messages
    """
    return render_template('messages/compose.html')

@bp.route('/templates', methods=['GET'])
@login_required
def templates():
    """Display message templates page.
    
    Returns:
        Rendered template with message templates
    """
    return render_template('messages/templates.html')

@bp.route('/history', methods=['GET'])
@login_required
def history():
    """Display message history page.
    
    Returns:
        Rendered template with message history
    """
    return render_template('messages/history.html')

# Keep the first definition (around line 470)
@bp.route('/scheduled', methods=['GET'])
@login_required
def scheduled():
    """Display scheduled messages page.
    
    Returns:
        Rendered template with scheduled messages
    """
    # Add the scheduled message retrieval logic from the second function if needed
    scheduled_messages = []  # Replace with actual scheduled message retrieval
    
    return render_template('messages/scheduled.html', messages=scheduled_messages)

# Remove the second definition (around line 670)
# DELETE THE FOLLOWING CODE:
# @bp.route('/scheduled', methods=['GET'])
# def scheduled():
#     """Display scheduled messages.
#     
#     Returns:
#         Rendered template with scheduled messages
#     """
#     if 'user_id' not in session or session.get('authenticated') is not True:
#         return redirect(url_for('auth.login'))
#     
#     # This is a placeholder - you'll need to implement scheduled message retrieval logic
#     scheduled_messages = []  # Replace with actual scheduled message retrieval
#     
#     return render_template('messages/scheduled.html', messages=scheduled_messages)

@bp.route('/templates/create', methods=['GET'])
@login_required  # Add decorator here
def templates_create():
    """Display template creation form.
    
    Returns:
        Rendered template creation form
    """
    return render_template('templates/create.html', edit_mode=False)


@bp.route('/templates/store', methods=['POST'])
@login_required  # Add decorator here
def templates_store():
    """Store a new template.
    
    Returns:
        Redirect to templates list
    """
    # This is a placeholder - you'll need to implement template storage logic
    flash('Template created successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/update', methods=['POST'])
@login_required
def templates_update():
    """Update an existing template.
    
    Returns:
        Redirect to templates list
    """
    
    # This is a placeholder - you'll need to implement template update logic
    flash('Template updated successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/create_category', methods=['POST'])
@login_required
def templates_create_category():
    """Create a new template category.
    
    Returns:
        Redirect to templates list
    """
    
    # This is a placeholder - you'll need to implement category creation logic
    flash('Category created successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/store_category', methods=['POST'])
@login_required
def templates_store_category():
    """Store a new template category.
    
    Returns:
        Redirect to templates list
    """
    
    # This is a placeholder - you'll need to implement category storage logic
    flash('Category stored successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/update_category', methods=['POST'])
@login_required
def templates_update_category():
    """Update an existing template category.
    
    Returns:
        Redirect to templates list
    """
    
    # This is a placeholder - you'll need to implement category update logic
    flash('Category updated successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/delete_category', methods=['POST'])
@login_required
def templates_delete_category():
    """Delete a template category.
    
    Returns:
        Redirect to templates list
    """
    
    # This is a placeholder - you'll need to implement category deletion logic
    flash('Category deleted successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/delete', methods=['POST'])
@login_required
def templates_delete():
    """Delete a template.
    
    Returns:
        Redirect to templates list
    """
    
    # This is a placeholder - you'll need to implement template deletion logic
    flash('Template deleted successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/get', methods=['GET'])
@login_required
def templates_get():
    """Get a template by ID.
    
    Returns:
        JSON response with template data
    """
    
    # This is a placeholder - you'll need to implement template retrieval logic
    template = {'id': request.args.get('id'), 'name': 'Sample Template', 'content': 'Sample content'}
    
    return jsonify({'success': True, 'template': template})


@bp.route('/templates/get_contact_data', methods=['GET'])
@login_required
def templates_get_contact_data():
    """Get contact data for template preview.
    
    Returns:
        JSON response with contact data
    """
    
    # This is a placeholder - you'll need to implement contact data retrieval logic
    contact = {'id': request.args.get('contact_id'), 'name': 'Sample Contact', 'phone': '+1234567890'}
    
    return jsonify({'success': True, 'contact': contact})


@bp.route('/templates/preview', methods=['GET'])
@login_required
def templates_preview():
    """Preview a template with contact data.
    
    Returns:
        JSON response with preview data
    """
    
    # This is a placeholder - you'll need to implement template preview logic
    preview = {'content': 'Sample preview content'}
    
    return jsonify({'success': True, 'preview': preview})


@bp.route('/templates/media/<int:id>', methods=['GET'])
@login_required
def templates_media(id):
    """Get template media.
    
    Args:
        id: Template ID
        
    Returns:
        Media file response
    """
    
    # This is a placeholder - you'll need to implement media retrieval logic
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], f'template_{id}_media.jpg')


@bp.route('/templates/duplicate/<int:id>', methods=['POST'])
@login_required
def templates_duplicate(id):
    """Duplicate a template.
    
    Args:
        id: Template ID
        
    Returns:
        Redirect to templates list
    """
    
    # This is a placeholder - you'll need to implement template duplication logic
    flash('Template duplicated successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/send_to_group', methods=['POST'])
@login_required
def send_to_group():
    """Send a message to all contacts in a group.
    
    Returns:
        JSON response with status of the message send operation
    """
    try:
        data = request.get_json()
        
        # Validate request data
        if not data or 'group_id' not in data or not data['group_id'] or 'content' not in data or not data['content']:
            return jsonify({'success': False, 'error': 'Group ID and message content are required'}), 400
        
        group_name = data['group_id']
        message_content = data['content']
        scheduled = data.get('scheduled', False)
        schedule_time = data.get('schedule_time') if scheduled else None
        
        # Get all contacts in the group
        from app.models.contact import Contact
        contacts = Contact.query.filter_by(group=group_name).all()
        
        if not contacts:
            return jsonify({'success': False, 'error': f'No contacts found in group {group_name}'}), 404
        
        # Create message service based on platform
        platform = data.get('platform', 'whatsapp').lower()
        message_service = MessageService.create(platform)
        
        # For scheduled messages
        if scheduled and schedule_time:
            # Queue messages for later sending
            from app.tasks.message_tasks import send_bulk_messages_task
            
            # Prepare messages list
            messages = []
            for contact in contacts:
                # Replace variables in message content
                personalized_message = message_content.replace('{name}', contact.name)
                personalized_message = personalized_message.replace('{phone}', contact.phone)
                personalized_message = personalized_message.replace('{email}', contact.email or '')
                personalized_message = personalized_message.replace('{group}', contact.group or '')
                
                messages.append({
                    'recipient': contact.phone,
                    'message': personalized_message,
                    'media_url': data.get('media_url')
                })
            
            # Schedule task
            from datetime import datetime
            schedule_datetime = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
            
            # Queue task
            task = send_bulk_messages_task.apply_async(
                args=[platform, messages],
                eta=schedule_datetime
            )
            
            return jsonify({
                'success': True,
                'scheduled': True,
                'task_id': task.id,
                'schedule_time': schedule_time,
                'message': f'Message scheduled to be sent to {len(contacts)} contacts in group {group_name}'
            })
        
        # For immediate sending
        success_count = 0
        failed_count = 0
        
        for contact in contacts:
            try:
                # Replace variables in message content
                personalized_message = message_content.replace('{name}', contact.name)
                personalized_message = personalized_message.replace('{phone}', contact.phone)
                personalized_message = personalized_message.replace('{email}', contact.email or '')
                personalized_message = personalized_message.replace('{group}', contact.group or '')
                
                # Send message
                result = message_service.send_message(
                    recipient=contact.phone,
                    message=personalized_message,
                    media_url=data.get('media_url')
                )
                
                # Save to database
                message = Message(
                    platform=platform,
                    recipient=contact.phone,
                    message_text=personalized_message,
                    media_url=data.get('media_url'),
                    status=result['status']
                )
                db.session.add(message)
                
                if result['status'] == 'sent':
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                current_app.logger.error(f"Error sending message to {contact.phone}: {str(e)}")
                failed_count += 1
        
        # Commit all messages to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'scheduled': False,
            'total': len(contacts),
            'sent': success_count,
            'failed': failed_count,
            'message': f'Sent messages to {success_count} contacts in group {group_name}'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error sending group message: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to send group message',
            'details': str(e)
        }), 500

@bp.route('/delete-history', methods=['POST'])
@login_required
def delete_history():
    """Delete a message from history.
    
    Returns:
        Redirect to message history page
    """
    message_id = request.form.get('message_id')
    
    if not message_id:
        flash('Message ID is required', 'error')
        return redirect(url_for('message.history'))
    
    try:
        # Find the message by ID
        message = Message.query.get(message_id)
        
        if not message:
            flash('Message not found', 'error')
            return redirect(url_for('message.history'))
        
        # Delete the message
        db.session.delete(message)
        db.session.commit()
        
        flash('Message deleted successfully', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting message: {str(e)}")
        flash(f"Error deleting message: {str(e)}", 'error')
        db.session.rollback()
    
    return redirect(url_for('message.history'))