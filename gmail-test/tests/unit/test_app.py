"""Tests for main application."""

import pytest
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.app import GmailAgent


class TestGmailAgent:
    """Test suite for GmailAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create Gmail agent."""
        return GmailAgent({
            "debug": True,
            "log_level": "INFO"
        })
    
    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.client is None
        assert agent.processor is not None
        assert agent.filter_service is not None
    
    def test_agent_authentication(self, agent):
        """Test agent authentication."""
        result = agent.authenticate("dummy_token")
        assert result is True
        assert agent.client is not None
    
    def test_get_statistics(self, agent):
        """Test getting statistics."""
        stats = agent.get_statistics()
        assert "emails_fetched" in stats
        assert "api_calls" in stats
    
    def test_shutdown(self, agent):
        """Test agent shutdown."""
        agent.authenticate("dummy_token")
        agent.shutdown()
        # Cache should be cleared
        assert agent.cache.get_size() == 0
    
    def test_handle_api_request(self, agent):
        """Test handling API request."""
        result = agent.handle_api_request("GET", "/emails", {"limit": 5})
        assert "status" in result
    
    def test_fetch_emails_not_authenticated(self, agent):
        """Test fetching emails without authentication."""
        with pytest.raises(RuntimeError):
            agent.fetch_emails()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
