"""Message routes for handling message sending operations."""
import os
import json  # Add this import
import time
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, session, redirect, url_for, render_template, flash
from flask_login import login_required, current_user  # Add this import
from flask import send_from_directory  # Add this import for templates_media route
from werkzeug.utils import secure_filename
from app.services.message_service import MessageService, WhatsAppService  # Added WhatsAppService import
from app.utils.validators import validate_message_request
from app.models.message import Message
from app.models.user import User
from app.models.whatsapp_session import WhatsAppSession  # Replace ApiCredential with WhatsAppSession
from app import db

bp = Blueprint('message', __name__)

@bp.route('/send', methods=['POST'])
@login_required
def send_message():
    """Send a message to a single recipient or multiple recipients, or save as draft.
    
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
            recipients = []
            is_bulk = False
            
            if recipient_type == 'individual':
                # Get selected contact
                individual_contact = request.form.get('individual_contacts')
                if individual_contact:
                    recipient = individual_contact
                    recipients = [individual_contact]
            elif recipient_type == 'multiple':
                # Get selected contacts
                multiple_contacts = request.form.getlist('multiple_contacts[]')
                if multiple_contacts:
                    is_bulk = True
                    recipients = multiple_contacts
                    # Set the first contact as the primary recipient for single message case
                    recipient = multiple_contacts[0]
            elif recipient_type == 'group':
                # Get selected group
                contact_group = request.form.get('contact_group')
                # Here you would fetch all contacts in this group
                # For now, just use the group ID as a placeholder
                recipient = f"group:{contact_group}"
                recipients = [recipient]
            elif recipient_type == 'custom':
                # Get custom numbers
                custom_numbers = request.form.get('custom_numbers')
                if custom_numbers:
                    # Split by comma or newline
                    numbers = [num.strip() for num in re.split(r'[,\n]+', custom_numbers) if num.strip()]
                    if numbers:
                        if len(numbers) > 1:
                            is_bulk = True
                            recipients = numbers
                        recipient = numbers[0]
                        recipients = numbers
            
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
        
        # Handle bulk sending if multiple recipients
        if is_bulk and recipients and len(recipients) > 1:
            # Initialize results
            results = []
            success_count = 0
            failed_count = 0
            
            # Send to each recipient
            for recipient_id in recipients:
                try:
                    # Send message to individual recipient
                    result = message_service.send_message(
                        recipient=recipient_id,
                        message=data['message'],
                        media_url=data.get('media_url')
                    )
                    
                    results.append({
                        'recipient': recipient_id,
                        'status': result.get('status', 'unknown'),
                        'success': result.get('success', False)
                    })
                    
                    if result.get('success', False):
                        success_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    current_app.logger.error(f"Error sending to recipient {recipient_id}: {str(e)}")
                    results.append({
                        'recipient': recipient_id,
                        'status': 'error',
                        'error': str(e),
                        'success': False
                    })
                    failed_count += 1
            
            # Set overall result
            result = {
                'success': success_count > 0,
                'status': 'partial' if failed_count > 0 else 'sent',
                'details': {
                    'total': len(recipients),
                    'success': success_count,
                    'failed': failed_count,
                    'results': results
                }
            }
        else:
            # Send to single recipient
            result = message_service.send_message(
                recipient=data['recipient'],
                message=data['message'],
                media_url=data.get('media_url')
            )
        
        # Check if this is a draft or scheduled message
        is_draft = request.form.get('is_draft') == '1'
        is_scheduled = request.form.get('schedule_message') == 'on'
        scheduled_time = None
        
        if is_scheduled:
            scheduled_time = request.form.get('schedule_time')
            if scheduled_time:
                scheduled_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        
        # Save to database
        if is_bulk and recipients and len(recipients) > 1 and not is_draft:
            # Save multiple messages for each recipient
            message_ids = []
            for recipient_id in recipients:
                # Find the result for this recipient if available
                recipient_result = result
                if 'details' in result and 'results' in result['details']:
                    for r in result['details']['results']:
                        if r['recipient'] == recipient_id:
                            recipient_result = r
                            break
                
                # Create message record
                message = Message(
                    platform=platform,
                    recipient=recipient_id,
                    message_text=data['message'],
                    media_url=data.get('media_url'),
                    status='draft' if is_draft else ('scheduled' if is_scheduled else recipient_result.get('status', result['status'])),
                    scheduled_at=scheduled_time,
                    user_id=current_user.id
                )
                db.session.add(message)
                message_ids.append(message.id)
            
            # Commit all messages at once
            db.session.commit()
            
            # Use the first message for response
            message = Message.query.get(message_ids[0]) if message_ids else None
        else:
            # Save single message
            message = Message(
                platform=platform,
                recipient=data['recipient'],
                message_text=data['message'],
                media_url=data.get('media_url'),
                status='draft' if is_draft else ('scheduled' if is_scheduled else result['status']),
                scheduled_at=scheduled_time,
                user_id=current_user.id
            )
            db.session.add(message)
            db.session.commit()
        
        # Return JSON or redirect based on request type
        if request.is_json:
            response_data = {
                'success': True,
                'status': message.status if message else 'unknown'
            }
            
            if message:
                response_data['message_id'] = message.id
            
            # Add bulk sending details if applicable
            if is_bulk and 'details' in result:
                response_data['bulk'] = True
                response_data['details'] = result['details']
            
            return jsonify(response_data)
        else:
            if is_draft:
                flash('Message saved as draft!', 'success')
                return redirect(url_for('message.drafts'))
            elif is_scheduled:
                if is_bulk:
                    flash(f'Scheduled {result["details"]["total"]} messages successfully!', 'success')
                else:
                    flash('Message scheduled successfully!', 'success')
                return redirect(url_for('message.scheduled'))
            else:
                if is_bulk:
                    success_count = result['details']['success']
                    total_count = result['details']['total']
                    if success_count == total_count:
                        flash(f'All {total_count} messages sent successfully!', 'success')
                    else:
                        flash(f'Sent {success_count} out of {total_count} messages successfully.', 'warning')
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
    # Get contacts from database
    from app.models.contact import Contact
    contacts = Contact.query.order_by(Contact.name).all()
    
    # Get contact groups from database
    from app.models.contact import ContactGroup
    groups = ContactGroup.query.all()
    
    # Check if there are phone numbers in the query string
    to_numbers = request.args.get('to', '')
    
    # Get message templates from database
    from app.models.message_queue import MessageTemplate
    templates = MessageTemplate.query.filter_by(is_active=True).all()
    
    return render_template('messages/compose.html', contacts=contacts, groups=groups, templates=templates, to_numbers=to_numbers)

@bp.route('/api/list_templates', methods=['GET'])
@login_required
def api_list_templates():
    """API endpoint to list message templates.
    
    Returns:
        JSON response with list of templates
    """
    try:
        # Get message templates from database
        from app.models.message_queue import MessageTemplate
        templates = MessageTemplate.query.filter_by(is_active=True).all()
        
        # Convert to list of dictionaries
        templates_list = [{
            'id': template.id,
            'name': template.name,
            'content': template.content,
            'category_id': template.category_id,
            'created_at': template.created_at.isoformat() if template.created_at else None,
            'updated_at': template.updated_at.isoformat() if template.updated_at else None
        } for template in templates]
        
        return jsonify({
            'success': True,
            'templates': templates_list
        })
    except Exception as e:
        current_app.logger.error(f"Error listing templates: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/templates', methods=['GET'])
@login_required
def templates():
    """Display message templates page.
    
    Returns:
        Rendered template with message templates
    """
    # Get message templates from database
    from app.models.message_queue import MessageTemplate
    templates = MessageTemplate.query.filter_by(is_active=True).all()
    
    # Get categories from database
    from app.models.template_category import MessageTemplateCategory
    categories = MessageTemplateCategory.query.filter_by(is_active=True).all()
    
    return render_template('messages/templates.html', templates=templates, categories=categories)

@bp.route('/history', methods=['GET'])
@login_required
def history():
    """Display message history page.
    
    Returns:
        Rendered template with message history
    """
    return render_template('messages/history.html')

# This route was removed to fix duplicate endpoint issue

@bp.route('/scheduled', methods=['GET'])
@login_required
def scheduled():
    """Display scheduled messages page.
    
    Returns:
        Rendered template with scheduled messages
    """
    # Get scheduled messages from database
    scheduled_messages = Message.query.filter_by(
        status='scheduled', 
        user_id=current_user.id
    ).order_by(Message.scheduled_at.asc()).all()
    
    return render_template('messages/scheduled.html', scheduled_messages=scheduled_messages)

@bp.route('/drafts', methods=['GET'])
@login_required
def drafts():
    """Display draft messages.
    
    Returns:
        Rendered drafts template with draft messages
    """
    # Get draft messages from database for current user
    draft_messages = Message.query.filter_by(
        status='draft',
        user_id=current_user.id
    ).order_by(Message.created_at.desc()).all()
    
    return render_template('messages/drafts.html', draft_messages=draft_messages)

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

@bp.route('/edit_draft/<int:message_id>', methods=['GET'])
@login_required
def edit_draft(message_id):
    """Edit a draft message.
    
    Args:
        message_id: ID of the draft message to edit
        
    Returns:
        Rendered compose template with draft message data
    """
    # Get the draft message
    message = Message.query.filter_by(id=message_id, status='draft', user_id=current_user.id).first_or_404()
    
    # Get contacts from database
    from app.models.contact import Contact
    contacts = Contact.query.all()
    
    # Get contact groups from database
    from app.models.contact import ContactGroup
    groups = ContactGroup.query.all()
    
    # Get message templates from database
    from app.models.message_queue import MessageTemplate
    templates = MessageTemplate.query.filter_by(is_active=True).all()
    
    return render_template('messages/compose.html', 
                          contacts=contacts, 
                          groups=groups, 
                          templates=templates,
                          draft_message=message)

@bp.route('/send_draft', methods=['POST'])
@login_required
def send_draft():
    """Send a draft message.
    
    Returns:
        JSON response with status of the message send operation
    """
    try:
        # Get the draft message ID
        message_id = request.form.get('message_id')
        if not message_id:
            return jsonify({'success': False, 'error': 'Message ID is required'})
        
        # Get the draft message
        message = Message.query.filter_by(id=message_id, status='draft', user_id=current_user.id).first()
        if not message:
            return jsonify({'success': False, 'error': 'Draft message not found'})
        
        # Create message service based on platform
        platform = message.platform.lower()
        message_service = MessageService.create(platform)
        
        # Send message
        result = message_service.send_message(
            recipient=message.recipient,
            message=message.message_text,
            media_url=message.media_url
        )
        
        # Update message status
        message.status = result['status']
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_id': message.id,
            'status': message.status
        })
        
    except Exception as e:
        current_app.logger.error(f"Error sending draft message: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to send draft message',
            'details': str(e)
        }), 500

@bp.route('/delete_message', methods=['POST'])
@login_required
def delete_message():
    """Delete a message (draft or scheduled).
    
    Returns:
        Redirect to appropriate page based on message type
    """
    try:
        # Get the message ID
        message_id = request.form.get('message_id')
        if not message_id:
            flash('Message ID is required', 'error')
            return redirect(url_for('message.drafts'))
        
        # Get the message
        message = Message.query.filter_by(id=message_id, user_id=current_user.id).first()
        if not message:
            flash('Message not found', 'error')
            return redirect(url_for('message.drafts'))
        
        # Store message status for redirect
        status = message.status
        
        # Delete the message
        db.session.delete(message)
        db.session.commit()
        
        flash('Message deleted successfully', 'success')
        
        # Redirect based on message type
        if status == 'draft':
            return redirect(url_for('message.drafts'))
        elif status == 'scheduled':
            return redirect(url_for('message.scheduled'))
        else:
            return redirect(url_for('message.index'))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting message: {str(e)}")
        flash(f'Error deleting message: {str(e)}', 'error')
        return redirect(url_for('message.drafts'))

@bp.route('/get_message_details', methods=['GET'])
@login_required
def get_message_details():
    """Get message details for display in modal.
    
    Returns:
        JSON response with message details
    """
    try:
        # Get the message ID
        message_id = request.args.get('message_id')
        if not message_id:
            return jsonify({'success': False, 'error': 'Message ID is required'})
        
        # Get the message
        message = Message.query.filter_by(id=message_id, user_id=current_user.id).first()
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'})
        
        # Format recipient display
        recipient_display = message.recipient
        if message.recipient.startswith('group:'):
            group_id = message.recipient.replace('group:', '')
            from app.models.contact import ContactGroup
            group = ContactGroup.query.get(group_id)
            if group:
                recipient_display = f'Group: {group.name}'
        elif message.recipient.isdigit():
            from app.models.contact import Contact
            contact = Contact.query.get(message.recipient)
            if contact:
                recipient_display = f'Contact: {contact.name}'
        
        # Return message details
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'recipient': recipient_display,
                'message_text': message.message_text,
                'media_url': message.media_url,
                'status': message.status,
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'scheduled_at': message.scheduled_at.strftime('%Y-%m-%d %H:%M:%S') if message.scheduled_at else None
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting message details: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get message details',
            'details': str(e)
        }), 500

@bp.route('/templates/create', methods=['GET'])
@login_required
def templates_create():
    """Display template creation form.
    
    Returns:
        Rendered template creation form
    """
    # Get categories from database
    from app.models.template_category import MessageTemplateCategory
    categories = MessageTemplateCategory.query.filter_by(is_active=True).all()
    
    return render_template('messages/create.html', edit_mode=False, categories=categories)


@bp.route('/templates/store', methods=['POST'])
@login_required
def templates_store():
    """Store a new template.
    
    Returns:
        Redirect to templates list
    """
    try:
        # Get form data
        name = request.form.get('name')
        content = request.form.get('content')
        category_id = request.form.get('category_id') or None
        
        # Validate required fields
        if not name or not content:
            flash('Template name and content are required', 'error')
            return redirect(url_for('message.templates_create'))
        
        # Handle media file upload if provided
        media_url = None
        if 'media' in request.files and request.files['media'].filename:
            media_file = request.files['media']
            
            # Generate a unique filename
            filename = secure_filename(media_file.filename)
            unique_filename = f"{int(time.time())}_{filename}"
            
            # Create media directory if it doesn't exist
            media_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates')
            os.makedirs(media_dir, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(media_dir, unique_filename)
            media_file.save(file_path)
            
            # Set the media URL for database storage
            media_url = f"/uploads/templates/{unique_filename}"
        
        # Import the template model
        from app.models.message_queue import MessageTemplate
        
        # Create new template
        template = MessageTemplate(
            name=name,
            content=content,
            category_id=category_id,
            media_url=media_url
        )
        
        # Save to database
        db.session.add(template)
        db.session.commit()
        
        flash('Template created successfully!', 'success')
        return redirect(url_for('message.templates'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating template: {str(e)}")
        flash(f'Error creating template: {str(e)}', 'error')
        return redirect(url_for('message.templates_create'))


@bp.route('/templates/edit/<int:template_id>', methods=['GET'])
@login_required
def templates_edit(template_id):
    """Display template edit form.
    
    Args:
        template_id: ID of the template to edit
        
    Returns:
        Rendered template edit form
    """
    try:
        # Import the template model
        from app.models.message_queue import MessageTemplate
        from app.models.template_category import MessageTemplateCategory
        
        # Find the template
        template = MessageTemplate.query.get(template_id)
        if not template:
            flash('Template not found', 'error')
            return redirect(url_for('message.templates'))
        
        # Get categories
        categories = MessageTemplateCategory.query.filter_by(is_active=True).all()
        
        return render_template('messages/create.html', template=template, categories=categories, edit_mode=True)
        
    except Exception as e:
        current_app.logger.error(f"Error loading template for edit: {str(e)}")
        flash(f'Error loading template: {str(e)}', 'error')
        return redirect(url_for('message.templates'))


@bp.route('/templates/update', methods=['POST'])
@login_required
def templates_update():
    """Update an existing template.
    
    Returns:
        Redirect to templates list
    """
    try:
        # Get form data
        template_id = request.form.get('id')
        name = request.form.get('name')
        content = request.form.get('content')
        category_id = request.form.get('category_id') or None
        
        # Validate required fields
        if not template_id or not name or not content:
            flash('Template ID, name, and content are required', 'error')
            return redirect(url_for('message.templates'))
        
        # Import the template model
        from app.models.message_queue import MessageTemplate
        
        # Find the template
        template = MessageTemplate.query.get(template_id)
        if not template:
            flash('Template not found', 'error')
            return redirect(url_for('message.templates'))
        
        # Handle media file upload if provided
        if 'media' in request.files and request.files['media'].filename:
            media_file = request.files['media']
            
            # Generate a unique filename
            filename = secure_filename(media_file.filename)
            unique_filename = f"{int(time.time())}_{filename}"
            
            # Create media directory if it doesn't exist
            media_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates')
            os.makedirs(media_dir, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(media_dir, unique_filename)
            media_file.save(file_path)
            
            # Delete old media file if exists
            if template.media_url:
                old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], template.media_url.lstrip('/'))
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            
            # Set the new media URL
            template.media_url = f"/uploads/templates/{unique_filename}"
        
        # Update template fields
        template.name = name
        template.content = content
        template.category_id = category_id
        template.updated_at = datetime.utcnow()
        
        # Save to database
        db.session.commit()
        
        flash('Template updated successfully!', 'success')
        return redirect(url_for('message.templates'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating template: {str(e)}")
        flash(f'Error updating template: {str(e)}', 'error')
        return redirect(url_for('message.templates'))


@bp.route('/templates/create_category', methods=['POST'])
@login_required
def templates_create_category():
    """Create a new template category.
    
    Returns:
        Redirect to templates list
    """
    try:
        # Get category name from form
        name = request.form.get('name')
        
        if not name:
            flash('Category name is required', 'error')
            return redirect(url_for('message.templates'))
        
        # Import the category model
        from app.models.template_category import MessageTemplateCategory
        
        # Check if category already exists
        existing_category = MessageTemplateCategory.query.filter_by(name=name).first()
        if existing_category:
            flash(f'Category "{name}" already exists', 'error')
            return redirect(url_for('message.templates'))
        
        # Create new category
        category = MessageTemplateCategory(name=name)
        db.session.add(category)
        db.session.commit()
        
        flash(f'Category "{name}" created successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating category: {str(e)}")
        flash(f'Error creating category: {str(e)}', 'error')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/store_category', methods=['POST'])
@login_required
def templates_store_category():
    """Store a new template category.
    
    Returns:
        Redirect to templates list
    """
    # This route is redundant with create_category, so we'll just redirect there
    return redirect(url_for('message.templates_create_category'), code=307)


@bp.route('/templates/update_category', methods=['POST'])
@login_required
def templates_update_category():
    """Update an existing template category.
    
    Returns:
        Redirect to templates list
    """
    try:
        # Get category ID and name from form
        category_id = request.form.get('id')
        name = request.form.get('name')
        
        if not category_id or not name:
            flash('Category ID and name are required', 'error')
            return redirect(url_for('message.templates'))
        
        # Import the category model
        from app.models.template_category import MessageTemplateCategory
        
        # Get category from database
        category = MessageTemplateCategory.query.get(category_id)
        if not category:
            flash(f'Category with ID {category_id} not found', 'error')
            return redirect(url_for('message.templates'))
        
        # Check if another category with the same name exists
        existing_category = MessageTemplateCategory.query.filter(
            MessageTemplateCategory.name == name,
            MessageTemplateCategory.id != category_id
        ).first()
        if existing_category:
            flash(f'Another category with name "{name}" already exists', 'error')
            return redirect(url_for('message.templates'))
        
        # Update category name
        category.name = name
        db.session.commit()
        
        flash(f'Category updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating category: {str(e)}")
        flash(f'Error updating category: {str(e)}', 'error')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/delete_category', methods=['POST'])
@login_required
def templates_delete_category():
    """Delete a template category.
    
    Returns:
        Redirect to templates list
    """
    try:
        # Get category ID from form
        category_id = request.form.get('id')
        
        if not category_id:
            flash('Category ID is required', 'error')
            return redirect(url_for('message.templates'))
        
        # Import the category model
        from app.models.template_category import MessageTemplateCategory
        from app.models.message_queue import MessageTemplate
        
        # Get category from database
        category = MessageTemplateCategory.query.get(category_id)
        if not category:
            flash(f'Category with ID {category_id} not found', 'error')
            return redirect(url_for('message.templates'))
        
        # Check if there are templates using this category
        templates_count = MessageTemplate.query.filter_by(category_id=category_id).count()
        if templates_count > 0:
            # Update templates to have no category
            MessageTemplate.query.filter_by(category_id=category_id).update({MessageTemplate.category_id: None})
            flash(f'Removed category from {templates_count} templates', 'info')
        
        # Delete the category
        db.session.delete(category)
        db.session.commit()
        
        flash('Category deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting category: {str(e)}")
        flash(f'Error deleting category: {str(e)}', 'error')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/delete', methods=['POST'])
@login_required
def templates_delete():
    """Delete a template.
    
    Returns:
        Redirect to templates list
    """
    try:
        # Get template ID from form
        template_id = request.form.get('id')
        
        if not template_id:
            flash('Template ID is required', 'error')
            return redirect(url_for('message.templates'))
        
        # Import the template model
        from app.models.message_queue import MessageTemplate
        
        # Find the template
        template = MessageTemplate.query.get(template_id)
        if not template:
            flash('Template not found', 'error')
            return redirect(url_for('message.templates'))
        
        # Delete media file if exists
        if template.media_url:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], template.media_url.lstrip('/'))
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Delete template from database
        db.session.delete(template)
        db.session.commit()
        
        flash('Template deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting template: {str(e)}")
        flash(f'Error deleting template: {str(e)}', 'error')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/get', methods=['GET'])
@login_required
def templates_get():
    """Get a template by ID.
    
    Returns:
        JSON response with template data
    """
    try:
        # Get template ID from query parameters
        template_id = request.args.get('id')
        
        if not template_id:
            return jsonify({'success': False, 'message': 'Template ID is required'})
        
        # Import the template model
        from app.models.message_queue import MessageTemplate
        
        # Find the template
        template = MessageTemplate.query.get(template_id)
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'})
        
        # Convert template to dictionary
        template_data = template.to_dict()
        
        return jsonify({'success': True, 'template': template_data})
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving template: {str(e)}")
        return jsonify({'success': False, 'message': f'Error retrieving template: {str(e)}'})


@bp.route('/templates/get_all', methods=['GET'])
@login_required
def templates_get_all():
    """Get all active templates.
    
    Returns:
        JSON response with all templates data
    """
    try:
        # Import the template model
        from app.models.message_queue import MessageTemplate
        
        # Get all active templates
        templates = MessageTemplate.query.filter_by(is_active=True).all()
        
        # Convert templates to list of dictionaries
        templates_data = [template.to_dict() for template in templates]
        
        return jsonify({'success': True, 'templates': templates_data})
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving templates: {str(e)}")
        return jsonify({'success': False, 'message': f'Error retrieving templates: {str(e)}'})


@bp.route('/templates/get_contact_data', methods=['GET'])
@login_required
def templates_get_contact_data():
    """Get contact data for template preview.
    
    Returns:
        JSON response with contact data
    """
    try:
        contact_id = request.args.get('contact_id')
        
        if not contact_id:
            # If no contact ID provided, return a sample contact
            return jsonify({
                'success': True, 
                'contact': {
                    'id': 0,
                    'name': 'Sample Contact',
                    'phone': '+1234567890',
                    'email': 'sample@example.com',
                    'group': 'Sample Group'
                }
            })
        
        # Import the contact model
        from app.models.contact import Contact
        
        # Find the contact
        contact = Contact.query.get(contact_id)
        if not contact:
            return jsonify({'success': False, 'message': 'Contact not found'})
        
        # Return contact data
        return jsonify({
            'success': True,
            'contact': contact.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving contact data: {str(e)}")
        return jsonify({'success': False, 'message': f'Error retrieving contact data: {str(e)}'})


@bp.route('/templates/preview', methods=['GET'])
@login_required
def templates_preview():
    """Preview a template with contact data.
    
    Returns:
        JSON response with preview data
    """
    try:
        # Get template ID and contact ID from query parameters
        template_id = request.args.get('template_id')
        contact_id = request.args.get('contact_id')
        
        if not template_id:
            return jsonify({'success': False, 'message': 'Template ID is required'})
        
        # Import the template model
        from app.models.message_queue import MessageTemplate
        
        # Find the template
        template = MessageTemplate.query.get(template_id)
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'})
        
        # Get contact data for personalization
        contact_data = {}
        if contact_id:
            # Import the contact model
            from app.models.contact import Contact
            
            # Find the contact
            contact = Contact.query.get(contact_id)
            if contact:
                contact_data = contact.to_dict()
            else:
                # Use sample data if contact not found
                contact_data = {
                    'name': 'Sample Contact',
                    'phone': '+1234567890',
                    'email': 'sample@example.com',
                    'group': 'Sample Group'
                }
        else:
            # Use sample data if no contact ID provided
            contact_data = {
                'name': 'Sample Contact',
                'phone': '+1234567890',
                'email': 'sample@example.com',
                'group': 'Sample Group'
            }
        
        # Personalize the template content
        content = template.content
        content = content.replace('{name}', contact_data.get('name', 'Contact Name'))
        content = content.replace('{phone}', contact_data.get('phone', 'Phone Number'))
        content = content.replace('{email}', contact_data.get('email', 'Email'))
        content = content.replace('{group}', contact_data.get('group', 'Group'))
        content = content.replace('{date}', datetime.now().strftime('%Y-%m-%d'))
        
        # Create preview data
        preview = {
            'content': content,
            'media_url': template.media_url,
            'contact': contact_data
        }
        
        return jsonify({'success': True, 'preview': preview})
        
    except Exception as e:
        current_app.logger.error(f"Error generating template preview: {str(e)}")
        return jsonify({'success': False, 'message': f'Error generating template preview: {str(e)}'})



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