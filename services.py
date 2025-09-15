from typing import Annotated, Dict, Any, List
from datetime import datetime, timedelta, timezone
import base64
import email
import io

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain_google_genai import GoogleGenerativeAI

# PDF reading libraries
try:
    import PyPDF2
    import fitz  # PyMuPDF
    import pdfplumber
    PDF_AVAILABLE = True
    print("DEBUG: PDF libraries loaded successfully")
except ImportError as e:
    PDF_AVAILABLE = False
    print(f"DEBUG: PDF libraries not available: {e}")

# Email sending imports
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Load environment variables from .env file
from dotenv import load_dotenv
import os
import json
import schedule
import time
import threading

# Firestore database 
from google.cloud import firestore
from google.oauth2 import service_account

# Load .env
load_dotenv()

# Get service account path - use absolute path
script_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(script_dir, "service-account.json")

# Load credentials explicitly
credentials = service_account.Credentials.from_service_account_file(cred_path)

# Firestore client
db = firestore.Client(project="agent-42b52", credentials=credentials)

Collection = "token"
token_doc_id = "1"

# Test Firestore connection
doc = db.collection(Collection).document(token_doc_id).get()

# Global variables for Gmail service and LLM
gmail_service = None
llm_instance = None

def authenticate_gmail():
    """Authenticate and return Gmail service object using ONLY Firestore and environment variables"""
    creds = None
    
    print("DEBUG: Starting Gmail authentication with Firestore database...")
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    

    # PRIORITY 2: Try Firestore database (primary method for stored credentials)
    if not creds:
        print("DEBUG: Using Firestore database for Gmail authentication")
        try:
            creds = load_token(token_doc_id)  # Using default user ID
            if creds:
                print("DEBUG: Firestore token loaded successfully")
                
                # Check if credentials need refresh
                if not creds.valid:
                    if creds.expired and creds.refresh_token:
                        try:
                            print("DEBUG: Firestore token expired, attempting refresh...")
                            creds.refresh(Request())
                            print("DEBUG: Firestore token refreshed successfully!")
                            
                            # Save refreshed token back to Firestore
                            try:
                                save_token(token_doc_id, creds)
                                print("DEBUG: Refreshed token saved to Firestore")
                            except Exception as e:
                                print(f"DEBUG: Could not save refreshed token to Firestore: {e}")
                                    
                        except Exception as e:
                            print(f"DEBUG: Token refresh failed: {e}")
                            # Remove corrupted token from Firestore
                            try:
                                db.collection(Collection).document(token_doc_id).delete()
                                print("DEBUG: Removed corrupted token from Firestore")
                            except:
                                pass
                            creds = None
            else:
                print("DEBUG: No token found in Firestore")
                creds = None
        except Exception as e:
            print(f"DEBUG: Failed to load token from Firestore: {e}")
            creds = None

    # If no credentials found, you'll need to run the OAuth flow manually
    if not creds:
        print("ERROR: No valid Gmail credentials found in Firestore")
        print("You need to run the OAuth flow to get initial credentials")
        raise ValueError("No valid Gmail credentials available. Please run OAuth flow first.")
    
    # Build and return Gmail service
    try:
        gmail_service = build('gmail', 'v1', credentials=creds)
        print("DEBUG: Gmail service built successfully")
        
        # Test the service with a simple call
        profile = gmail_service.users().getProfile(userId="me").execute()
        print(f"DEBUG: Gmail authentication verified for: {profile.get('emailAddress', 'Unknown')}")
        
        return gmail_service
        
    except Exception as e:
        print(f"DEBUG: Failed to build Gmail service: {e}")
        raise ValueError(f"Failed to create Gmail service: {e}")

def initialize_services():
    global gmail_service, llm_instance

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in .env file")
    
    llm_instance = GoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=google_api_key
    )

    gmail_service = authenticate_gmail()
    return gmail_service, llm_instance

def ensure_services():
    """Ensure Gmail and LLM services are initialized"""
    global gmail_service, llm_instance
    if gmail_service is None or llm_instance is None:
        initialize_services()

def save_token(user_id: str, creds: Credentials):
    """Save Gmail credentials to Firestore"""
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    db.collection(Collection).document(token_doc_id).set(token_data)

def load_token(user_id: str) -> Credentials | None:
    """Load Gmail credentials from Firestore"""
    doc = db.collection(Collection).document(token_doc_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    return Credentials(
        token=data["token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )

def get_email_content(msg_data):
    """Extract full email content from message data"""
    payload = msg_data['payload']
    content = ""
    
    # Function to decode base64 content
    def decode_data(data):
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        return ""
    
    # Handle different email structures
    if 'parts' in payload:
        # Multi-part email
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    content += decode_data(part['body']['data'])
            elif part['mimeType'] == 'text/html':
                if 'data' in part['body'] and not content:
                    content += decode_data(part['body']['data'])
            elif 'parts' in part:  # Nested parts
                for nested_part in part['parts']:
                    if nested_part['mimeType'] == 'text/plain' and 'data' in nested_part['body']:
                        content += decode_data(nested_part['body']['data'])
    else:
        # Single part email
        if payload['mimeType'] == 'text/plain':
            if 'data' in payload['body']:
                content += decode_data(payload['body']['data'])
        elif payload['mimeType'] == 'text/html':
            if 'data' in payload['body']:
                content += decode_data(payload['body']['data'])
    
    return content.strip()

def send_email(to: str, subject: str, body: str) -> str:
    try:
        ensure_services()
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = gmail_service.users().messages().send(
            userId="me",
            body={'raw': raw_message}
        ).execute()

        return "Email sent successfully with ID: " + result['id'] + " sent to: " + to
    except Exception as e:
        return "Error sending email: " + str(e)

def draft_email(to:str , subject:str , body:str) -> str :
    try :
        ensure_services()
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = gmail_service.users().drafts().create(
            userId="me",
            body={'message': {'raw': raw_message}}
        ).execute()

        return "Draft created successfully with ID: " + result['id'] + " for: " + to
    except Exception as e:
        return "Error creating draft: " + str(e)

def reply_to_email(message_id: str, reply_body: str) -> str:
    """Reply to a specific email"""
    try:
        ensure_services()
        
        # Get original message
        original_msg = gmail_service.users().messages().get(userId="me", id=message_id).execute()
        headers = original_msg['payload']['headers']
        
        # Extract original sender and subject
        original_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
        original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        message_id_header = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
        
        # Create reply subject
        reply_subject = original_subject if original_subject.startswith('Re: ') else f"Re: {original_subject}"
        
        # Get thread ID for proper threading
        thread_id = original_msg.get('threadId', '')
        
        # Create reply message
        reply_message = MIMEText(reply_body)
        reply_message['to'] = original_from
        reply_message['subject'] = reply_subject
        reply_message['In-Reply-To'] = message_id_header
        reply_message['References'] = message_id_header
        
        raw_message = base64.urlsafe_b64encode(reply_message.as_bytes()).decode()
        
        # Send with threadId to ensure proper threading
        send_body = {'raw': raw_message}
        if thread_id:
            send_body['threadId'] = thread_id
        
        result = gmail_service.users().messages().send(
            userId="me",
            body=send_body
        ).execute()
        
        return f"Reply sent successfully! ID: {result['id']}"
    except Exception as e:
        return f"Error sending reply: {str(e)}"

def smart_reply_to_mail(message_id: str, reply_body: str, custom_subject: str = None) -> str:
    """Send a simple reply to an email with your custom message and optional custom subject"""
    try:
        ensure_services()
        
        # Get original message
        original_msg = gmail_service.users().messages().get(userId="me", id=message_id).execute()
        headers = original_msg['payload']['headers']
        
        original_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
        original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        message_id_header = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
        
        # Get thread ID for proper threading
        thread_id = original_msg.get('threadId', '')
        
        # Create reply subject - use custom subject if provided, otherwise use "Re: original subject"
        if custom_subject:
            reply_subject = custom_subject
        else:
            reply_subject = original_subject if original_subject.startswith('Re: ') else f"Re: {original_subject}"
        
        # Create and send reply message with proper threading
        reply_message = MIMEText(reply_body)
        reply_message['to'] = original_from
        reply_message['subject'] = reply_subject
        reply_message['In-Reply-To'] = message_id_header
        reply_message['References'] = message_id_header
        
        raw_message = base64.urlsafe_b64encode(reply_message.as_bytes()).decode()
        
        # Send with threadId to ensure proper threading
        send_body = {'raw': raw_message}
        if thread_id:
            send_body['threadId'] = thread_id
        
        result = gmail_service.users().messages().send(
            userId="me",
            body=send_body
        ).execute()
        
        return json.dumps({
            "success": True,
            "message_id": result['id'],
            "status": "Reply sent successfully!",
            "reply_info": {
                "reply_body": reply_body,
                "reply_subject": reply_subject,
                "thread_id": thread_id
            },
            "original_email_info": {
                "from": original_from,
                "subject": original_subject,
                "message_id": message_id
            },
            "sent_to": original_from
        }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error sending reply: {str(e)}"
        }, indent=2)

def search_emails(query: str, max_results: int = 20) -> str:
    """Search emails with advanced Gmail search syntax"""
    try:
        ensure_services()
        
        result = gmail_service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = result.get('messages', [])
        search_results = []
        
        for msg in messages[:10]:  # Limit detailed results
            msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
            headers = msg_detail['payload']['headers']
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
            
            search_results.append({
                'message_id': msg['id'],
                'subject': subject,
                'from': sender,
                'date': date,
                'snippet': msg_detail.get('snippet', '')[:150]
            })
        
        return json.dumps({
            'total_results': len(messages),
            'query': query,
            'results': search_results,
            'search_examples': [
                'from:example@gmail.com',
                'subject:"meeting"', 
                'has:attachment',
                'is:unread',
                'after:2024/1/1',
                'label:important'
            ]
        }, indent=2)
        
    except Exception as e:
        return f"Error searching emails: {str(e)}"