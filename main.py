from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken
from typing import Any, List
import json
import os
from pydantic import BaseModel

# Import all user-facing functions from services
from services import (
    send_email,
    draft_email, 
    reply_to_email,
    search_emails,
    forward_email,
    get_email_analysis_by_date,
    get_email_analysis_by_message_id,
    analyze_last_n_emails_by_keyword,
    analyze_emails_by_multiple_keywords,
    analyze_last_n_emails
)

# Get environment variables like PuchAI
TOKEN = os.environ.get("TOKEN", "gmail_agent_token")
MY_NUMBER = os.environ.get("MY_NUMBER", "918328653599")

# RichToolDescription pattern for better MCP tool metadata
class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

# SimpleBearerAuthProvider exactly like PuchAI
class SimpleBearerAuthProvider(BearerAuthProvider):
    """
    A simple BearerAuthProvider that does not require any specific configuration.
    It allows any valid bearer token to access the MCP server.
    For a more complete implementation that can authenticate dynamically generated tokens,
    please use `BearerAuthProvider` with your public key or JWKS URI.
    """

    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(
            public_key=k.public_key, jwks_uri=None, issuer=None, audience=None
        )
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="unknown",
                scopes=[],
                expires_at=None,  # No expiration for simplicity
            )
        return None

# Initialize FastMCP server like PuchAI
mcp = FastMCP(
    "Gmail MCP Agent",
    auth=SimpleBearerAuthProvider(TOKEN),
)

# ==================== TOOL DESCRIPTIONS ====================

SEND_EMAIL_DESCRIPTION = RichToolDescription(
    description="Send a basic email to a recipient with subject and body",
    use_when="User wants to send a new email message",
    side_effects="Connects to Gmail API and sends an email message"
)

DRAFT_EMAIL_DESCRIPTION = RichToolDescription(
    description="Create an email draft without sending it",
    use_when="User wants to create a draft for later editing or sending",
    side_effects="Creates a draft in Gmail that can be edited later"
)

REPLY_EMAIL_DESCRIPTION = RichToolDescription(
    description="Reply to an existing email message",
    use_when="User wants to reply to a specific email using message ID",
    side_effects="Sends a reply email maintaining the conversation thread"
)

SEARCH_EMAILS_DESCRIPTION = RichToolDescription(
    description="Search for emails using Gmail search syntax",
    use_when="User wants to find specific emails using queries like 'from:sender@domain.com' or keywords",
    side_effects="Searches Gmail and returns matching email information"
)

FORWARD_EMAIL_DESCRIPTION = RichToolDescription(
    description="Forward an email to another recipient with optional additional message",
    use_when="User wants to forward an existing email to someone else",
    side_effects="Sends a forwarded email to the specified recipient"
)

EMAIL_ANALYSIS_BY_DATE_DESCRIPTION = RichToolDescription(
    description="Get AI analysis of emails from a specific date (YYYY-MM-DD format)",
    use_when="User wants to see analysis of all emails from a particular date",
    side_effects="Analyzes emails and may store results in Firestore database"
)

EMAIL_ANALYSIS_BY_MESSAGE_DESCRIPTION = RichToolDescription(
    description="Get AI analysis of a specific email using message ID",
    use_when="User wants detailed AI analysis of a particular email",
    side_effects="Analyzes single email with AI and stores results in database"
)

KEYWORD_ANALYSIS_DESCRIPTION = RichToolDescription(
    description="Analyze last N emails by keyword with AI insights",
    use_when="User wants to find and analyze emails containing specific keywords",
    side_effects="Searches emails, analyzes with AI, and stores results in database"
)

MULTIPLE_KEYWORDS_DESCRIPTION = RichToolDescription(
    description="Analyze emails by multiple keywords with flexible matching (any/all)",
    use_when="User wants complex email analysis using multiple search terms",
    side_effects="Searches and analyzes emails with multiple criteria, stores results"
)

DAILY_SUMMARY_DESCRIPTION = RichToolDescription(
    description="Get daily analysis summary from database for a specific date",
    use_when="User wants to retrieve previously generated daily email analysis",
    side_effects="Retrieves stored analysis data from Firestore database"
)

LAST_N_EMAILS_DESCRIPTION = RichToolDescription(
    description="Analyze the last N emails without any filters - comprehensive AI analysis of recent emails",
    use_when="User wants overall analysis of their most recent emails without specific search criteria",
    side_effects="Analyzes recent emails with AI, stores results in database, provides comprehensive insights"
)

# ==================== EMAIL SENDING TOOLS ====================

@mcp.tool(description=SEND_EMAIL_DESCRIPTION.model_dump_json())
async def send_email_basic(to: str, subject: str, body: str) -> str:
    """Send a basic email to a recipient with subject and body"""
    return send_email(to, subject, body)

@mcp.tool(description=DRAFT_EMAIL_DESCRIPTION.model_dump_json())
async def create_email_draft(to: str, subject: str, body: str) -> str:
    """Create an email draft without sending it"""
    return draft_email(to, subject, body)

@mcp.tool(description=REPLY_EMAIL_DESCRIPTION.model_dump_json())
async def reply_to_message(message_id: str, reply_body: str) -> str:
    """Reply to an existing email message"""
    return reply_to_email(message_id, reply_body)

@mcp.tool(description=SEARCH_EMAILS_DESCRIPTION.model_dump_json())
async def find_emails(query: str, max_results: int = 20) -> str:
    """Search for emails using Gmail search syntax"""
    return search_emails(query, max_results)

@mcp.tool(description=FORWARD_EMAIL_DESCRIPTION.model_dump_json())
async def forward_email_tool(message_id: str, to_email: str, additional_message: str = "") -> str:
    """Forward an email to another recipient with optional additional message"""
    return forward_email(message_id, to_email, additional_message)

# ==================== EMAIL ANALYSIS TOOLS ====================

@mcp.tool(description=EMAIL_ANALYSIS_BY_DATE_DESCRIPTION.model_dump_json())
async def get_email_analysis_by_date_tool(date_str: str) -> str:
    """Get AI analysis of emails from a specific date (YYYY-MM-DD format)"""
    return get_email_analysis_by_date(date_str)

@mcp.tool(description=EMAIL_ANALYSIS_BY_MESSAGE_DESCRIPTION.model_dump_json())
async def get_email_analysis_by_message_tool(message_id: str) -> str:
    """Get AI analysis of a specific email using message ID"""
    return get_email_analysis_by_message_id(message_id)

@mcp.tool(description=KEYWORD_ANALYSIS_DESCRIPTION.model_dump_json())
async def analyze_emails_by_keyword(keyword: str, num_emails: int = 20) -> str:
    """Analyze last N emails by keyword with AI insights"""
    return analyze_last_n_emails_by_keyword(keyword, num_emails)

@mcp.tool(description=MULTIPLE_KEYWORDS_DESCRIPTION.model_dump_json())
async def analyze_emails_by_keywords(keywords: List[str], num_emails: int = 30, match_type: str = "any") -> str:
    """Analyze emails by multiple keywords with flexible matching (any/all)"""
    return analyze_emails_by_multiple_keywords(keywords, num_emails, match_type)

@mcp.tool(description=LAST_N_EMAILS_DESCRIPTION.model_dump_json())
async def analyze_recent_emails(num_emails: int) -> str:
    """Analyze the last N emails without any filters - comprehensive AI analysis of recent emails"""
    return analyze_last_n_emails(num_emails)

# ==================== SERVER UTILITY TOOLS ====================

VALIDATE_DESCRIPTION = RichToolDescription(
    description="Validate server connection and return server information",
    use_when="Client needs to validate server connection or get server metadata",
    side_effects="Returns server information for validation purposes"
)

ABOUT_DESCRIPTION = RichToolDescription(
    description="Get comprehensive information about the Gmail MCP server",
    use_when="Client needs server capabilities, features, and metadata information",
    side_effects="Returns detailed server information and available features"
)

@mcp.tool(description=VALIDATE_DESCRIPTION.model_dump_json())
async def validate() -> str:
    """Validate server connection and return phone number (required by PuchAI)"""
    return MY_NUMBER

@mcp.tool(description=ABOUT_DESCRIPTION.model_dump_json())
async def about() -> str:
    """Get comprehensive information about the Gmail MCP server"""
    return json.dumps({
        "name": "Gmail MCP Agent",
        "description": "Advanced Gmail management and AI-powered email analysis server",
        "version": "2.0",
        "capabilities": {
            "email_operations": [
                "send_email",
                "create_draft", 
                "reply_to_email",
                "forward_email",
                "search_emails"
            ],
            "ai_analysis": [
                "single_email_analysis",
                "date_based_analysis", 
                "keyword_analysis",
                "multi_keyword_analysis",
                "tech_student_priority_scoring"
            ],
            "data_storage": [
                "firestore_integration",
                "analysis_history",
                "daily_summaries"
            ]
        },
        "ai_model": "Google Gemini 1.5 Flash",
        "database": "Google Firestore",
        "authentication": "Gmail OAuth2 + Service Account"
    }, indent=2)

async def main():
    port = int(os.environ.get("PORT", 8080))
    await mcp.run_async(
        "streamable-http",
        host="0.0.0.0",
        port=port,
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

