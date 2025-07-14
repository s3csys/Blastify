"""Application entry point."""

import os
from app import create_app, db
from app.models.user import User
from app.models.message import Message
from app.models.whatsapp_session import WhatsAppSession

# Set environment variables for webdriver-manager
os.environ['WDM_SSL_VERIFY'] = '0'
os.environ['WDM_LOCAL'] = '1'
os.environ['WDM_CACHE_PATH'] = os.path.join(os.getcwd(), 'app_data', 'webdriver_cache')
# Disable PowerShell usage for Windows
os.environ['WDM_USE_POWERSHELL'] = 'false'

app = create_app()

# Ensure database tables are created and admin user exists
from app import initialize_admin_user
with app.app_context():
    db.create_all()
    initialize_admin_user(app)

@app.shell_context_processor
def make_shell_context():
    """Add objects to Flask shell context."""
    return {
        'db': db,
        'User': User,
        'Message': Message,
        'WhatsAppSession': WhatsAppSession
    }

if __name__ == '__main__':
    app.run(
        host=app.config['FLASK_HOST'],
        port=app.config['FLASK_PORT'],
        debug=app.config['DEBUG_MODE']
    )