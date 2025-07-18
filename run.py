"""Application entry point."""

import os
from app import create_app, db
from app.models.user import User
from app.models.message import Message
from app.models.api_credential import ApiCredential

# Set environment variables for webdriver-manager
os.environ['WDM_SSL_VERIFY'] = '0'
os.environ['WDM_LOCAL'] = '1'
os.environ['WDM_CACHE_PATH'] = os.path.join(os.getcwd(), 'app_data', 'webdriver_cache')
# Disable PowerShell usage for Windows
os.environ['WDM_USE_POWERSHELL'] = 'false'

app = create_app()

# Ensure database tables are created
with app.app_context():
    db.create_all()

@app.shell_context_processor
def make_shell_context():
    """Add objects to Flask shell context."""
    return {
        'db': db,
        'User': User,
        'Message': Message,
        'ApiCredential': ApiCredential
    }

if __name__ == '__main__':
    app.run(debug=True)