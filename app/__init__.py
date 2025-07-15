"""Blastify application initialization."""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_login import LoginManager
from dotenv import load_dotenv, find_dotenv, set_key
from datetime import datetime

# Load environment variables from .env file with override to allow dynamic reloading
load_dotenv(override=True)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def initialize_admin_user(app):
    """Initialize admin user from environment variables if it doesn't exist.
    Also updates the admin user if environment variables have changed.
    
    Args:
        app: Flask application instance
    """
    from app.models.user import User
    
    admin_username = app.config['ADMIN_USERNAME']
    admin_email = app.config['ADMIN_EMAIL']
    admin_password = app.config['ADMIN_PASSWORD']
    
    # Check if admin user exists
    admin_user = User.query.filter_by(username=admin_username).first()
    
    if not admin_user:
        app.logger.info(f"Creating admin user: {admin_username}")
        admin_user = User(
            username=admin_username,
            email=admin_email,
            is_active=True
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.commit()
        app.logger.info(f"Admin user created successfully")
    else:
        # Check if admin user details need updating
        updated = False
        
        # Update email if changed
        if admin_user.email != admin_email:
            app.logger.info(f"Updating admin email from {admin_user.email} to {admin_email}")
            admin_user.email = admin_email
            updated = True
        
        # Always ensure admin user is active
        if not admin_user.is_active:
            app.logger.info(f"Activating admin user account")
            admin_user.is_active = True
            updated = True
            
        # Commit changes if any updates were made
        if updated:
            db.session.commit()
            app.logger.info(f"Admin user updated successfully")
        else:
            app.logger.info(f"Admin user already exists and is up to date")


def configure_logging(app):
    """Configure application logging based on environment variables.
    
    Args:
        app: Flask application instance
    """
    # Create logs directory if it doesn't exist
    log_dir = app.config['LOG_DIR']
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set log level
    log_level_name = app.config['LOG_LEVEL']
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=app.config['LOG_FORMAT'],
        datefmt=app.config['LOG_DATE_FORMAT']
    )
    
    # Configure application logger
    app_log_file = os.path.join(log_dir, app.config['APP_LOG'])
    app_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    app_handler.setFormatter(logging.Formatter(
        app.config['LOG_FORMAT'],
        app.config['LOG_DATE_FORMAT']
    ))
    app_handler.setLevel(log_level)
    app.logger.addHandler(app_handler)
    
    # Configure access logger if not in testing mode
    if not app.testing:
        access_log_file = os.path.join(log_dir, app.config['ACCESS_LOG'])
        access_handler = RotatingFileHandler(
            access_log_file,
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        access_handler.setFormatter(logging.Formatter(
            app.config['LOG_FORMAT'],
            app.config['LOG_DATE_FORMAT']
        ))
        access_logger = logging.getLogger('werkzeug')
        access_logger.addHandler(access_handler)
        
    # Configure error logger
    error_log_file = os.path.join(log_dir, app.config['ERROR_LOG'])
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    error_handler.setFormatter(logging.Formatter(
        app.config['LOG_FORMAT'],
        app.config['LOG_DATE_FORMAT']
    ))
    error_handler.setLevel(logging.ERROR)
    app.logger.addHandler(error_handler)

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
    
    # Configure logging
    configure_logging(app)
    
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
        # Initialize database tables
    with app.app_context():
        db.create_all()
        initialize_admin_user(app)
    
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
            
            # Get current time in UTC
            now = datetime.now(timezone.utc)
            
            # Handle timezone-naive datetimes (convert both to naive for comparison)
            if dt.tzinfo is None:
                # If input is naive, make comparison with naive now
                now = now.replace(tzinfo=None)
            else:
                # If input has timezone, ensure it's UTC
                dt = dt.astimezone(timezone.utc)
                
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
    
    # API routes
    from app.routes.api import bp as api_bp
    app.register_blueprint(api_bp)
    
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
    
    # WhatsApp Bulk Messaging routes
    from app.routes.whatsapp_bulk import bp as whatsapp_bulk_bp
    app.register_blueprint(whatsapp_bulk_bp)
    
    # Selenium Integration Check routes
    from app.routes.selenium_check import bp as selenium_check_bp
    app.register_blueprint(selenium_check_bp)
    
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