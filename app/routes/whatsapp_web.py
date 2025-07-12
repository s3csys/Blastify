import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.whatsapp_session import WhatsAppSession
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
    return render_template('whatsapp/settings.html')