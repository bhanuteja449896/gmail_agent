"""Gmail Agent - Advanced Email Automation System

This package provides comprehensive email automation, filtering, and management
capabilities with a focus on production-ready code and extensive testing.
"""

__version__ = "1.0.0"
__author__ = "Gmail Agent Team"
__description__ = "Advanced Gmail automation and email management system"

from src.core.gmail_client import GmailClient
from src.core.email_processor import EmailProcessor
from src.models.email import Email, EmailThread, Label
from src.services.filter_service import FilterService
from src.services.template_service import TemplateService

__all__ = [
    "GmailClient",
    "EmailProcessor",
    "Email",
    "EmailThread",
    "Label",
    "FilterService",
    "TemplateService",
]
