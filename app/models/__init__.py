"""Models package initialization."""

from app import db

# Import models here so they are registered with SQLAlchemy
from app.models.user import User
from app.models.contact import Contact
from app.models.message import Message
from app.models.settings import Settings

# Import WhatsApp models
from app.models.whatsapp_session import WhatsAppSession, WhatsAppDevice
from app.models.message_queue import MessageTemplate, MessageQueue, MessageStatus