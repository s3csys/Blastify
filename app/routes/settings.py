import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

# Create blueprint
bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/', methods=['GET'])
@login_required
def index():
    """Display main settings page.
    
    Returns:
        Rendered template with settings options
    """
    return render_template('settings/index.html')

@bp.route('/theme', methods=['GET'])
@login_required
def theme():
    """Display theme settings page.
    
    Returns:
        Rendered template with theme settings
    """
    return render_template('settings/theme.html')

@bp.route('/theme/update', methods=['POST'])
@login_required
def update_theme():
    """Update user theme preference.
    
    Returns:
        JSON response with status
    """
    theme_name = request.json.get('theme')
    if not theme_name:
        return jsonify({'success': False, 'message': 'Theme name is required'}), 400
        
    # In a real implementation, you would save this to the user's profile
    # For now, we'll just return success
    return jsonify({'success': True, 'message': 'Theme updated successfully'}), 200