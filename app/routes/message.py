"""Message routes for handling message sending operations."""
import os
import json  # Add this import
from flask import Blueprint, request, jsonify, current_app, session, redirect, url_for, render_template, flash
from flask_login import login_required, current_user  # Add this import
from app.services.message_service import MessageService, WhatsAppService  # Added WhatsAppService import
from app.utils.validators import validate_message_request
from app.models.message import Message
from app.models.user import User
from app.models.api_credential import ApiCredential  # Add this import
from app import db

bp = Blueprint('message', __name__)

@bp.route('/send', methods=['POST'])
def send_message():
    """Send a message to a single recipient.
    
    Returns:
        JSON response with status of the message send operation
    """
    try:
        data = request.get_json()
        
        # Validate request data
        errors = validate_message_request(data)
        if errors:
            return jsonify({'success': False, 'errors': errors}), 400
        
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
        
        return jsonify({
            'success': True,
            'message_id': message.id,
            'status': result['status']
        })
        
    except Exception as e:
        current_app.logger.error(f"Error sending message: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to send message',
            'details': str(e)
        }), 500

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
def connect_messaging():
    """Connect to WhatsApp or Telegram messaging services."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    # Initialize variables
    whatsapp_connected = False
    telegram_connected = False
    
    # Create WhatsApp service to manage credentials
    whatsapp_service = WhatsAppService()
    
    # Get available credential sets
    whatsapp_credentials = ApiCredential.get_credential_sets('whatsapp')
    
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
                # Get instance ID, token, and credential name from form if provided
                instance_id = request.form.get('instance_id')
                api_token = request.form.get('api_token')
                credential_name = request.form.get('credential_name')
                
                # Check if we're loading an existing credential set
                load_credential_id = request.form.get('load_credential_id')
                
                if load_credential_id:
                    # Find the credential set by name
                    for cred in whatsapp_credentials:
                        if cred.get('name') == load_credential_id:
                            instance_id = cred.get('instance_id')
                            api_token = cred.get('api_token')
                            credential_name = cred.get('name')
                            break
                
                # Update credentials if provided
                if instance_id and api_token:
                    # If no credential name provided, use instance ID as name
                    if not credential_name:
                        credential_name = f"WhatsApp-{instance_id[:8]}"
                        
                    # Save credentials using the service method
                    if whatsapp_service.save_credentials(instance_id, api_token, credential_name):
                        flash(f"Green API credentials saved as '{credential_name}'.", "success")
                        
                        # Try to connect with the new credentials
                        try:
                            if whatsapp_service.is_connected():
                                whatsapp_connected = True
                                flash("Successfully connected to WhatsApp", "success")
                            else:
                                flash("Credentials saved but connection failed. Please check your credentials.", "warning")
                        except Exception as e:
                            flash(f"Credentials saved but error checking connection: {str(e)}", "warning")
                    else:
                        flash("Failed to save Green API credentials", "error")
                else:
                    flash("Instance ID and API Token are required", "error")
                
            except Exception as e:
                current_app.logger.error(f"Error connecting to WhatsApp: {str(e)}")
                flash(f"Error connecting to WhatsApp: {str(e)}", "error")
        
        elif service == 'telegram':
            # Similar implementation for Telegram
            pass
    
    return render_template('connect_messaging.html', 
                          whatsapp_connected=whatsapp_connected,
                          telegram_connected=telegram_connected,
                          whatsapp_credentials=whatsapp_credentials,
                          user=user)


@bp.route('/disconnect-service/<service>', methods=['POST'])
def disconnect_service(service):
    """Disconnect from a messaging service.
    
    Args:
        service: The service to disconnect from (whatsapp, telegram)
        
    Returns:
        Redirect to the connect messaging page
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    try:
        if service == 'whatsapp':
            # Implement WhatsApp disconnection logic for Green API
            try:
                # Create WhatsApp service
                whatsapp_service = WhatsAppService()
                
                # Logout from Green API
                if whatsapp_service.is_connected():
                    # Call logout method
                    whatsapp_service.green_api.account.logout()
                
                # Remove credentials file
                credentials_file = os.path.join(os.getcwd(), 'app_data', 'whatsapp_session', 'credentials.json')
                if os.path.exists(credentials_file):
                    os.remove(credentials_file)
                
                # Verify disconnection
                if not whatsapp_service.is_connected():
                    flash("Successfully disconnected from WhatsApp", "success")
                else:
                    flash("Failed to disconnect from WhatsApp. Please try again.", "error")
            except Exception as e:
                current_app.logger.error(f"Error during WhatsApp logout: {str(e)}")  # Changed from logger to current_app.logger
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


@bp.route('/manage-credentials', methods=['POST'])
def manage_credentials():
    """Manage API credentials (add, edit, delete).
    
    Returns:
        Redirect to the connect messaging page
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    action = request.form.get('action')
    service = request.form.get('service')
    
    if service == 'whatsapp':
        whatsapp_service = WhatsAppService()
        
        if action == 'add' or action == 'edit':
            # Get form data
            instance_id = request.form.get('instance_id')
            api_token = request.form.get('api_token')
            credential_name = request.form.get('credential_name')
            
            if not instance_id or not api_token or not credential_name:
                flash("All fields are required", "error")
            else:
                # Save credentials
                if whatsapp_service.save_credentials(instance_id, api_token, credential_name):
                    flash(f"Credentials '{credential_name}' saved successfully", "success")
                else:
                    flash("Failed to save credentials", "error")
                    
        elif action == 'delete':
            credential_name = request.form.get('credential_name')
            
            if not credential_name:
                flash("Credential name is required", "error")
            else:
                # Delete credentials
                if whatsapp_service.delete_credential(credential_name):
                    flash(f"Credentials '{credential_name}' deleted successfully", "success")
                else:
                    flash("Failed to delete credentials", "error")
                    
        elif action == 'connect':
            credential_name = request.form.get('credential_name')
            
            if not credential_name:
                flash("Credential name is required", "error")
            else:
                # Load and connect with selected credentials
                if whatsapp_service.load_credential_by_name(credential_name):
                    try:
                        if whatsapp_service.is_connected():
                            flash(f"Successfully connected to WhatsApp using '{credential_name}'", "success")
                        else:
                            flash(f"Loaded credentials '{credential_name}' but connection failed", "warning")
                    except Exception as e:
                        flash(f"Error checking connection: {str(e)}", "error")
                else:
                    flash(f"Failed to load credentials '{credential_name}'", "error")
    
    return redirect(url_for('message.connect_messaging'))


# Add these imports at the top if not already present
import base64
from flask import jsonify

# Add these new routes
@bp.route('/generate-whatsapp-qr', methods=['POST'])
def generate_whatsapp_qr():
    """Generate a QR code for WhatsApp Web authentication.
    
    Returns:
        JSON response with QR code data
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        credential_name = request.form.get('credential_name')
        if not credential_name:
            return jsonify({'success': False, 'error': 'Credential name is required'}), 400
        
        # Create WhatsApp service with the selected credential
        whatsapp_service = WhatsAppService()
        if not whatsapp_service.load_credential_by_name(credential_name):
            return jsonify({'success': False, 'error': 'Failed to load credentials'}), 400
        
        # Generate QR code
        qr_code_base64 = whatsapp_service.generate_qr_code()
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
def check_whatsapp_connection():
    """Check if WhatsApp is connected after QR code scan.
    
    Returns:
        JSON response with connection status
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        credential_name = request.form.get('credential_name')
        if not credential_name:
            return jsonify({'success': False, 'error': 'Credential name is required'}), 400
        
        # Create WhatsApp service with the selected credential
        whatsapp_service = WhatsAppService()
        if not whatsapp_service.load_credential_by_name(credential_name):
            return jsonify({'success': False, 'error': 'Failed to load credentials'}), 400
        
        # Check connection status
        connected = whatsapp_service.is_connected()
        
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
def templates_update():
    """Update an existing template.
    
    Returns:
        Redirect to templates list
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    # This is a placeholder - you'll need to implement template update logic
    flash('Template updated successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/create_category', methods=['POST'])
def templates_create_category():
    """Create a new template category.
    
    Returns:
        Redirect to templates list
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    # This is a placeholder - you'll need to implement category creation logic
    flash('Category created successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/store_category', methods=['POST'])
def templates_store_category():
    """Store a new template category.
    
    Returns:
        Redirect to templates list
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    # This is a placeholder - you'll need to implement category storage logic
    flash('Category stored successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/update_category', methods=['POST'])
def templates_update_category():
    """Update an existing template category.
    
    Returns:
        Redirect to templates list
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    # This is a placeholder - you'll need to implement category update logic
    flash('Category updated successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/delete_category', methods=['POST'])
def templates_delete_category():
    """Delete a template category.
    
    Returns:
        Redirect to templates list
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    # This is a placeholder - you'll need to implement category deletion logic
    flash('Category deleted successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/delete', methods=['POST'])
def templates_delete():
    """Delete a template.
    
    Returns:
        Redirect to templates list
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    # This is a placeholder - you'll need to implement template deletion logic
    flash('Template deleted successfully!', 'success')
    
    return redirect(url_for('message.templates'))


@bp.route('/templates/get', methods=['GET'])
def templates_get():
    """Get a template by ID.
    
    Returns:
        JSON response with template data
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # This is a placeholder - you'll need to implement template retrieval logic
    template = {'id': request.args.get('id'), 'name': 'Sample Template', 'content': 'Sample content'}
    
    return jsonify({'success': True, 'template': template})


@bp.route('/templates/get_contact_data', methods=['GET'])
def templates_get_contact_data():
    """Get contact data for template preview.
    
    Returns:
        JSON response with contact data
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # This is a placeholder - you'll need to implement contact data retrieval logic
    contact = {'id': request.args.get('contact_id'), 'name': 'Sample Contact', 'phone': '+1234567890'}
    
    return jsonify({'success': True, 'contact': contact})


@bp.route('/templates/preview', methods=['GET'])
def templates_preview():
    """Preview a template with contact data.
    
    Returns:
        JSON response with preview data
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # This is a placeholder - you'll need to implement template preview logic
    preview = {'content': 'Sample preview content'}
    
    return jsonify({'success': True, 'preview': preview})


@bp.route('/templates/media/<int:id>', methods=['GET'])
def templates_media(id):
    """Get template media.
    
    Args:
        id: Template ID
        
    Returns:
        Media file response
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    # This is a placeholder - you'll need to implement media retrieval logic
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], f'template_{id}_media.jpg')


@bp.route('/templates/duplicate/<int:id>', methods=['GET'])
def templates_duplicate(id):
    """Duplicate a template.
    
    Args:
        id: Template ID
        
    Returns:
        Redirect to templates list
    """
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    # This is a placeholder - you'll need to implement template duplication logic
    flash('Template duplicated successfully!', 'success')
    
    return redirect(url_for('message.templates'))


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