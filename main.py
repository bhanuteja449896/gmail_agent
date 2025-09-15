from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ImageContent, EmbeddedResource
from typing import Any
import json

# Import all user-facing functions from services
from services import (
    send_email,
    draft_email, 
    reply_to_email,
    smart_reply_with_ai,
    search_emails
)

# Initialize FastMCP server
mcp = FastMCP("Gmail MCP Agent")

# ==================== EMAIL SENDING TOOLS ====================

@mcp.tool()
async def send_email_basic(to: str, subject: str, body: str) -> str:
    """Send a basic email to a recipient with subject and body"""
    return send_email(to, subject, body)

@mcp.tool()
async def create_email_draft(to: str, subject: str, body: str) -> str:
    """Create an email draft without sending it"""
    return draft_email(to, subject, body)

@mcp.tool()
async def reply_to_message(message_id: str, reply_body: str) -> str:
    """Reply to an existing email message"""
    return reply_to_email(message_id, reply_body)

@mcp.tool()
async def smart_reply_to_message(message_id: str, reply_body: str, custom_subject: str = None) -> str:
    """Send a custom reply to an email with proper threading"""
    return smart_reply_with_ai(message_id, reply_body, custom_subject)

@mcp.tool()
async def find_emails(query: str, max_results: int = 20) -> str:
    """Search for emails using Gmail search syntax"""
    return search_emails(query, max_results)

if __name__ == "__main__":
    mcp.run()
