"""Template service for email composition."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TemplateService:
    """Advanced email template management service."""
    
    def __init__(self):
        """Initialize template service."""
        self.templates: Dict[str, Dict] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default templates."""
        default_templates = {
            "welcome": {
                "subject": "Welcome to {{company}}!",
                "body": "Hello {{name}},\n\nWelcome to {{company}}!\n\n{{message}}",
                "category": "onboarding"
            },
            "notification": {
                "subject": "Notification: {{type}}",
                "body": "{{name}},\n\n{{notification}}\n\nTimestamp: {{timestamp}}",
                "category": "notification"
            },
            "support": {
                "subject": "Support: {{issue}}",
                "body": "Dear {{name}},\n\nThank you for contacting support.\n\nYour issue: {{issue}}\n\n{{response}}",
                "category": "support"
            }
        }
        self.templates.update(default_templates)
    
    def add_template(self, name: str, template: Dict[str, str]) -> None:
        """Add a template."""
        self.templates[name] = template
        logger.info(f"Added template: {name}")
    
    def get_template(self, name: str) -> Optional[Dict]:
        """Get template by name."""
        return self.templates.get(name)
    
    def render(self, template_name: str, variables: Dict[str, str]) -> Optional[Dict]:
        """Render a template with variables."""
        template = self.get_template(template_name)
        if not template:
            return None
        
        rendered = {}
        for key, value in template.items():
            if isinstance(value, str):
                rendered[key] = value
                for var, val in variables.items():
                    rendered[key] = rendered[key].replace(f"{{{{{var}}}}}", str(val))
        
        return rendered
