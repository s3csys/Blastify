"""Blastify application initialization."""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_login import LoginManager  # Add this import
from dotenv import load_dotenv
from datetime import datetime  # Add this import

# Load environment variables from .env file
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()  # Add this line

def create_app(config_class=None):
    """Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__, 
                template_folder='../templates',  # Point to the templates folder
                static_folder='../static')       # Point to the static folder
    
    # Load configuration
    if config_class is None:
        app.config.from_object('config.Config')
    else:
        app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Setup CORS
    CORS(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # User loader function for Flask-Login
    from app.models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    register_blueprints(app)
    
    # Add root route that redirects to dashboard
    @app.route('/')
    def index():
        """Redirect root URL to dashboard."""
        return redirect(url_for('dashboard.index'))
    
    # Initialize database
    @app.before_first_request
    def initialize_database():
        """Create database tables if they don't exist."""
        db.create_all()
    
    # Add context processor for templates
    @app.context_processor
    def inject_now():
        """Make now variable available to all templates."""
        return {'now': datetime.utcnow()}
    
    # Register custom template filters
    @app.template_filter('humanize')
    def humanize_filter(dt):
        """Format a datetime to a human readable string."""
        if dt is None:
            return ""
        
        try:
            import humanize
            from datetime import datetime, timezone
            
            # Ensure dt is timezone-aware for comparison
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
                
            now = datetime.now(timezone.utc)
            return humanize.naturaltime(dt, when=now)
        except (ImportError, AttributeError, ValueError):
            # Fallback to basic ISO format if humanize fails
            return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Configure logging
    configure_logging(app)
    
    return app

def register_blueprints(app):
    """Register all blueprints with the application."""
    # API routes - keep this for API endpoints
    from app.routes.message import bp as message_bp
    app.register_blueprint(message_bp, url_prefix='/messages')  # Changed from '/api/messages' to '/messages'
    
    # Web routes
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.routes.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    from app.routes.contact import bp as contact_bp
    app.register_blueprint(contact_bp, url_prefix='/contacts')
    
    # WhatsApp API routes
    from app.routes.whatsapp import whatsapp_bp
    app.register_blueprint(whatsapp_bp)
    
    # WhatsApp Web routes
    from app.routes.whatsapp_web import bp as whatsapp_web_bp
    app.register_blueprint(whatsapp_web_bp)
    
    # Settings routes
    from app.routes.settings import bp as settings_bp
    app.register_blueprint(settings_bp)

def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/blastify.log', 
                                          maxBytes=10240, 
                                          backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Blastify startup')