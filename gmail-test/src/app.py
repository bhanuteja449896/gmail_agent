"""Main application module."""

import logging
import sys
from typing import Optional

from src.core.gmail_client import GmailClient, GmailClientBuilder
from src.core.email_processor import EmailProcessor, BulkEmailProcessor
from src.services.filter_service import FilterService, TemplateService
from src.utils.helpers import ConfigurationManager, EmailStatisticsCollector, CacheManager
from src.api.routes import GmailAPI, APIRouter


logger = logging.getLogger(__name__)


class GmailAgent:
    """
    Main Gmail Agent application.
    
    Orchestrates all components for email management and automation.
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize Gmail Agent.
        
        Args:
            config: Configuration dictionary
        """
        self.config_manager = ConfigurationManager()
        if config:
            self.config_manager.load_from_dict(config)
        
        self.client: Optional[GmailClient] = None
        self.processor = EmailProcessor()
        self.bulk_processor = BulkEmailProcessor()
        self.filter_service = FilterService()
        self.template_service = TemplateService()
        self.stats_collector = EmailStatisticsCollector()
        self.cache = CacheManager()
        self.api = GmailAPI()
        self.router = APIRouter()
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self.config_manager.get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def authenticate(self, token: str, refresh_token: Optional[str] = None) -> bool:
        """
        Authenticate with Gmail API.
        
        Args:
            token: Access token
            refresh_token: Refresh token
            
        Returns:
            True if authentication successful
        """
        try:
            self.client = (GmailClientBuilder()
                          .with_debug(self.config_manager.get("debug", False))
                          .build())
            
            result = self.client.authenticate(token, refresh_token)
            if result:
                logger.info("Gmail agent authenticated successfully")
                self.stats_collector.record_fetch()
            return result
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.stats_collector.record_error()
            return False
    
    def fetch_emails(self, query: str = "", max_results: int = 10):
        """Fetch emails from Gmail."""
        if not self.client:
            raise RuntimeError("Not authenticated")
        
        try:
            emails, token = self.client.fetch_emails(query, max_results)
            self.stats_collector.record_fetch(len(emails))
            return emails, token
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            self.stats_collector.record_error()
            raise
    
    def send_email(self, to: list, subject: str, body: str, **kwargs):
        """Send an email."""
        if not self.client:
            raise RuntimeError("Not authenticated")
        
        try:
            message_id = self.client.send_email(to, subject, body, **kwargs)
            self.stats_collector.record_send()
            logger.info(f"Email sent: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            self.stats_collector.record_error()
            raise
    
    def apply_filters(self, emails: list) -> dict:
        """Apply filters to emails."""
        try:
            results = {}
            for email in emails:
                actions = self.filter_service.apply_filters(email)
                if actions:
                    results[email.get("id")] = actions
            
            logger.info(f"Applied filters to {len(results)} emails")
            return results
        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")
            self.stats_collector.record_error()
            raise
    
    def get_statistics(self) -> dict:
        """Get application statistics."""
        return self.stats_collector.get_stats()
    
    def process_emails(self, emails: list, processor_name: Optional[str] = None):
        """Process emails in batch."""
        try:
            results = self.bulk_processor.process_batch(emails, processor_name)
            logger.info(f"Processed {len(results)} emails")
            return results
        except Exception as e:
            logger.error(f"Failed to process emails: {e}")
            self.stats_collector.record_error()
            raise
    
    def handle_api_request(self, method: str, path: str, params: dict = None):
        """Handle API request."""
        try:
            response = self.router.route(method, path, params)
            return response.to_dict()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def shutdown(self):
        """Shutdown the agent."""
        try:
            if self.client:
                self.client.close()
            self.cache.clear()
            logger.info("Gmail agent shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def main():
    """Main entry point."""
    # Initialize agent
    agent = GmailAgent({
        "debug": False,
        "log_level": "INFO"
    })
    
    logger.info("Gmail Agent started")
    
    try:
        # Dummy authentication
        agent.authenticate("dummy_token")
        
        # Example usage
        stats = agent.get_statistics()
        logger.info(f"Current stats: {stats}")
        
    finally:
        agent.shutdown()


if __name__ == "__main__":
    main()
