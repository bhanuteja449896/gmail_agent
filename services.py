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
import re
import pytz

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

def analyze_email_with_ai(email_data):
    """Standardized AI analysis of email using tech student priority scoring"""
    ensure_services()
    
    # Extract email details
    headers = email_data["payload"]["headers"]
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
    date = next((h["value"] for h in headers if h["name"] == "Date"), "No Date")
    message_id = email_data.get('id', '')
    content = get_email_content(email_data)
    
    # Create improved prompt with tech student priority scoring
    prompt = f"""
    You are analyzing emails for a TECH STUDENT. Use this importance    scoring:

    EMAIL DETAILS:
    FROM: {sender}
    SUBJECT: {subject}
    CONTENT: {content[:1500]}

    IMPORTANCE SCORING FOR TECH STUDENT:
    - Interview/Meeting invitations (scheduled): 10/10 (HIGHEST -   immediate action needed)
    - Work meetings with specific dates/times: 10/10
    - Assignment/Project deadlines: 9-10/10
    - Job applications responses/next steps: 9/10
    - Job opportunities to apply: 7-8/10 (important but not urgent)
    - Academic/Course related: 7-9/10
    - Personal important messages: 6-7/10
    - Promotional/Marketing emails: 1-2/10
    - Social media notifications: 2-3/10
    - Newsletters/General updates: 3-4/10

    URGENCY RULES:
    - Same day meetings = HIGH
    - Next day meetings = HIGH  
    - This week deadlines = HIGH
    - Job opportunities = MEDIUM
    - Promotions = LOW

    Return this JSON with DETAILED LINKS structure:
    {{
        "basic_info": {{
            "from": "{sender}",
            "subject": "{subject}",
            "date": "{date}",
            "content_summary": "One sentence summary focusing on ACTION     NEEDED"
        }},
        "classification": {{
            "category": "interview|meeting|job_opportunity|academic|    personal|promotional|social|newsletter",
            "importance_score": "CALCULATE based on TECH STUDENT    priorities above",
            "urgency": "high|medium|low - based on time sensitivity",
            "is_job_related": "true if career/internship/job related",
            "is_meeting_related": "true if scheduled meeting/interview/ call", 
            "requires_action": "true if immediate response/action needed"
        }},
        "extracted_data": {{
            "links": [
                {{
                    "url": "the actual link URL",
                    "type": "meeting|job_application|interview| company_page|general",
                    "company": "company name if applicable",
                    "meeting_type": "interview|team_meeting|one_on_one| webinar|null",
                    "date": "YYYY-MM-DD format if date mentioned",
                    "time": "HH:MM format if time mentioned", 
                    "summary": "brief description of what this link is  for",
                    "platform": "zoom|teams|google_meet|linkedin|   company_portal|other"
                }}
            ],
            "action_items": ["specific actions needed with timeframes"],
            "deadlines": ["exact dates/times mentioned"]
        }}
    }}

    Return ONLY the JSON:"""
    
    try:
        # Get LLM response
        response = llm_instance.invoke(prompt)
        
        # Clean the response and find JSON
        response = response.strip()
        
        # Find JSON in the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            email_analysis = json.loads(json_match.group())
            return email_analysis
        else:
            raise ValueError("No valid JSON found in LLM response")
        
    except Exception as e:
        print(f"DEBUG: AI analysis failed for message {message_id}: {e}")
        
        # Smart fallback analysis
        def calculate_fallback_importance(subject, sender, content):
            subject_lower = subject.lower()
            sender_lower = sender.lower()
            content_lower = content.lower() if content else ""
            
            # HIGHEST PRIORITY: Scheduled meetings/interviews
            if any(word in subject_lower for word in ['interview', 'meeting scheduled', 'tomorrow', 'today']):
                return 10
            elif any(word in content_lower for word in ['11:00 am', '11 am', 'zoom', 'teams', 'meet.google', 'scheduled']):
                return 10
            elif any(word in subject_lower for word in ['meeting', 'call', 'interview']):
                return 9
            elif any(word in subject_lower for word in ['deadline', 'due', 'urgent', 'asap', 'immediate']):
                return 9
            elif any(word in subject_lower for word in ['assignment', 'project', 'submission']):
                return 8
            elif any(word in subject_lower for word in ['job', 'internship', 'opportunity', 'position', 'career']):
                return 7
            elif any(word in subject_lower for word in ['course', 'class', 'university', 'college']):
                return 7
            elif 'personal' in sender_lower or not any(word in sender_lower for word in ['.com', 'noreply']):
                return 6
            elif any(word in sender_lower for word in ['noreply', 'no-reply', 'marketing']):
                return 2
            elif any(word in subject_lower for word in ['newsletter', 'update', 'promotion']):
                return 3
            else:
                return 5
        
        importance = calculate_fallback_importance(subject, sender, content)
        
        # Extract basic links from content for fallback
        fallback_links = []
        if content:
            urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
            for url in urls[:3]:
                fallback_links.append({
                    "url": url,
                    "type": "general",
                    "company": "",
                    "meeting_type": None,
                    "date": "",
                    "time": "",
                    "summary": "Link extracted from email content",
                    "platform": "other"
                })
        
        return {
            "basic_info": {
                "from": sender,
                "subject": subject, 
                "date": date,
                "content_summary": f"Email from {sender.split('@')[0] if '@' in sender else sender} - analysis used fallback logic"
            },
            "classification": {
                "category": "job_opportunity" if "job" in subject.lower() else "meeting" if "meeting" in subject.lower() or "interview" in subject.lower() else "promotional" if "noreply" in sender.lower() else "personal",
                "importance_score": importance,
                "urgency": "high" if importance >= 8 else "medium" if importance >= 6 else "low",
                "is_job_related": any(word in subject.lower() for word in ["job", "internship", "career", "position", "opportunity"]),
                "is_meeting_related": any(word in subject.lower() for word in ["meeting", "interview", "schedule", "call"]),
                "requires_action": importance >= 7
            },
            "extracted_data": {
                "links": fallback_links,
                "action_items": ["Check email content - analysis failed"] if importance >= 7 else [],
                "deadlines": []
            }
        }


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


def search_emails(query: str, max_results: int) -> str:
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

def forward_email(message_id: str, to_email: str, additional_message: str = "") -> str:
    """Forward an email to another recipient with optional additional message"""
    try:
        ensure_services()
        
        # Get original message
        original_msg = gmail_service.users().messages().get(userId="me", id=message_id, format='full').execute()
        headers = original_msg['payload']['headers']
        
        # Extract original email details
        original_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
        original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        original_date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        original_to = next((h['value'] for h in headers if h['name'] == 'To'), '')
        
        # Get original content
        original_content = get_email_content(original_msg)
        
        # Create forward subject
        forward_subject = original_subject if original_subject.startswith('Fwd: ') else f"Fwd: {original_subject}"
        
        # Create forwarded message body
        forward_body = f"{additional_message}\n\n" if additional_message else ""
        forward_body += f"---------- Forwarded message ----------\n"
        forward_body += f"From: {original_from}\n"
        forward_body += f"Date: {original_date}\n"
        forward_body += f"Subject: {original_subject}\n"
        forward_body += f"To: {original_to}\n\n"
        forward_body += original_content
        
        # Create and send forwarded message
        forward_message = MIMEMultipart()
        forward_message['to'] = to_email
        forward_message['subject'] = forward_subject
        forward_message.attach(MIMEText(forward_body, 'plain'))
        
        # Handle attachments if any
        if 'parts' in original_msg['payload']:
            for part in original_msg['payload']['parts']:
                if part.get('filename') and part['body'].get('attachmentId'):
                    attachment = gmail_service.users().messages().attachments().get(
                        userId="me", 
                        messageId=message_id,
                        id=part['body']['attachmentId']
                    ).execute()
                    
                    file_data = base64.urlsafe_b64decode(attachment['data'])
                    mime_part = MIMEBase('application', 'octet-stream')
                    mime_part.set_payload(file_data)
                    encoders.encode_base64(mime_part)
                    mime_part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{part["filename"]}"'
                    )
                    forward_message.attach(mime_part)
        
        raw_message = base64.urlsafe_b64encode(forward_message.as_bytes()).decode()
        
        result = gmail_service.users().messages().send(
            userId="me",
            body={'raw': raw_message}
        ).execute()
        
        return json.dumps({
            "success": True,
            "message_id": result['id'],
            "status": "Email forwarded successfully!",
            "forwarded_to": to_email,
            "original_from": original_from,
            "subject": forward_subject
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error forwarding email: {str(e)}"
        }, indent=2)

def get_email_analysis_by_date(date_str: str) -> str:
    """Analyze emails by date - simple analysis with message_id as key"""
    try:
        ensure_services()
        
        # Search for emails from specific date
        query = f"after:{date_str} before:{date_str}"
        
        result = gmail_service.users().messages().list(
            userId="me",
            q=query,
            maxResults=50
        ).execute()
        
        messages = result.get('messages', [])
        
        if not messages:
            return json.dumps({
                "success": True,
                "date": date_str,
                "message": "No emails found for this date"
            }, indent=2)
        
        # Analyze each email and store with message_id as key
        analyzed_data = {}
        
        for msg in messages:
            msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
            
            # Use existing analyze_email_with_ai function
            ai_analysis = analyze_email_with_ai(msg_detail)
            
            # Store analyzed data with message_id as key
            analyzed_data[msg['id']] = ai_analysis
        
        return json.dumps({
            "success": True,
            "date": date_str,
            "num_emails_found": len(messages),
            "analyzed_emails": analyzed_data
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error analyzing emails by date: {str(e)}"
        }, indent=2)

def get_email_analysis_by_message_id(message_id: str) -> str:
    """Analyze specific email by message ID - simple analysis with message_id as key"""
    try:
        ensure_services()
        
        # Get message details
        msg_detail = gmail_service.users().messages().get(userId="me", id=message_id).execute()
        
        # Use existing analyze_email_with_ai function
        ai_analysis = analyze_email_with_ai(msg_detail)
        
        # Return with message_id as key
        analyzed_data = {message_id: ai_analysis}
        
        return json.dumps({
            "success": True,
            "message_id": message_id,
            "analyzed_emails": analyzed_data
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error analyzing email: {str(e)}"
        }, indent=2)

def analyze_last_n_emails_by_keyword(keyword: str, num_emails: int) -> str:
    """Analyze emails by keyword - simple analysis with message_id as key"""
    try:
        ensure_services()
        
        # Search for emails containing the keyword
        query = f"{keyword}"
        
        result = gmail_service.users().messages().list(
            userId="me",
            q=query,
            maxResults=num_emails
        ).execute()
        
        messages = result.get('messages', [])
        
        if not messages:
            return json.dumps({
                "success": True,
                "keyword": keyword,
                "num_requested": num_emails,
                "message": f"No emails found containing keyword: '{keyword}'"
            }, indent=2)
        
        # Analyze each email and store with message_id as key
        analyzed_data = {}
        
        for msg in messages:
            msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
            
            # Use existing analyze_email_with_ai function
            ai_analysis = analyze_email_with_ai(msg_detail)
            
            # Store analyzed data with message_id as key
            analyzed_data[msg['id']] = ai_analysis
        
        return json.dumps({
            "success": True,
            "keyword": keyword,
            "num_emails_requested": num_emails,
            "num_emails_found": len(messages),
            "analyzed_emails": analyzed_data
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error analyzing emails by keyword: {str(e)}"
        }, indent=2)

def analyze_emails_by_multiple_keywords(keywords: List[str], num_emails: int, match_type: str = "any") -> str:
    """Analyze emails by multiple keywords - simple analysis with message_id as key"""
    try:
        ensure_services()
        
        # Build search query based on match type
        if match_type.lower() == "all":
            # All keywords must be present
            query = " AND ".join([f'"{keyword}"' for keyword in keywords])
        else:
            # Any keyword can be present (default)
            query = " OR ".join([f'"{keyword}"' for keyword in keywords])
        
        result = gmail_service.users().messages().list(
            userId="me",
            q=query,
            maxResults=num_emails
        ).execute()
        
        messages = result.get('messages', [])
        
        if not messages:
            return json.dumps({
                "success": True,
                "keywords": keywords,
                "match_type": match_type,
                "num_requested": num_emails,
                "message": f"No emails found containing keywords: {keywords}"
            }, indent=2)
        
        # Analyze each email and store with message_id as key
        analyzed_data = {}
        
        for msg in messages:
            msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
            
            # Use existing analyze_email_with_ai function
            ai_analysis = analyze_email_with_ai(msg_detail)
            
            # Store analyzed data with message_id as key
            analyzed_data[msg['id']] = ai_analysis
        
        return json.dumps({
            "success": True,
            "keywords": keywords,
            "match_type": match_type,
            "num_emails_requested": num_emails,
            "num_emails_found": len(messages),
            "analyzed_emails": analyzed_data
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error analyzing emails by multiple keywords: {str(e)}"
        }, indent=2)


def analyze_last_n_emails(num_emails: int) -> str:
    """Analyze the last N emails - simple analysis with message_id as key"""
    try:
        ensure_services()
        
        # Get the most recent emails
        result = gmail_service.users().messages().list(
            userId="me",
            maxResults=num_emails
        ).execute()
        
        messages = result.get('messages', [])
        
        if not messages:
            return json.dumps({
                "success": True,
                "num_requested": num_emails,
                "message": "No emails found in mailbox"
            }, indent=2)
        
        # Analyze each email and store with message_id as key
        analyzed_data = {}
        
        for msg in messages:
            msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
            
            # Use existing analyze_email_with_ai function
            ai_analysis = analyze_email_with_ai(msg_detail)
            
            # Store analyzed data with message_id as key
            analyzed_data[msg['id']] = ai_analysis
        
        return json.dumps({
            "success": True,
            "num_emails_requested": num_emails,
            "num_emails_found": len(messages),
            "analyzed_emails": analyzed_data
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error analyzing last {num_emails} emails: {str(e)}"
        }, indent=2)


# def get_daily_analysis_summary(date_str: str) -> str:
#     """Get daily analysis summary from database"""
#     try:
#         doc = db.collection("daily_email_analysis").document(f"daily_{date_str}").get()
        
#         if not doc.exists:
#             return json.dumps({
#                 "success": False,
#                 "date": date_str,
#                 "error": "No daily analysis found for this date"
#             }, indent=2)
        
#         daily_data = doc.to_dict()
        
#         return json.dumps({
#             "success": True,
#             "date": date_str,
#             "daily_analysis": daily_data
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error retrieving daily analysis: {str(e)}"
#         }, indent=2)


# def analyze_keyword_trends_over_time(keyword: str, days_back: int = 30) -> str:
#     """Analyze how a keyword appears in emails over time with trend analysis"""
#     try:
#         ensure_services()
        
#         # Calculate date range
#         end_date = datetime.now(timezone.utc)
#         start_date = end_date - timedelta(days=days_back)
        
#         # Search for emails with keyword in date range
#         start_date_str = start_date.strftime('%Y/%m/%d')
#         end_date_str = end_date.strftime('%Y/%m/%d')
#         query = f'{keyword} after:{start_date_str} before:{end_date_str}'
        
#         result = gmail_service.users().messages().list(
#             userId="me",
#             q=query,
#             maxResults=100
#         ).execute()
        
#         messages = result.get('messages', [])
        
#         if not messages:
#             return json.dumps({
#                 "success": True,
#                 "keyword": keyword,
#                 "days_analyzed": days_back,
#                 "date_range": f"{start_date_str} to {end_date_str}",
#                 "message": f"No emails found containing keyword: '{keyword}' in the specified time range",
#                 "analysis": "No trend analysis available"
#             }, indent=2)
        
#         # Group emails by date for trend analysis
#         daily_counts = {}
#         weekly_counts = {}
#         keyword_contexts = []
#         senders_over_time = {}
        
#         for msg in messages:
#             msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
#             headers = msg_detail['payload']['headers']
            
#             subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
#             sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
#             date_str = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
#             content = get_email_content(msg_detail)
            
#             # Parse date for grouping
#             try:
#                 from email.utils import parsedate_to_datetime
#                 email_date = parsedate_to_datetime(date_str)
#                 day_key = email_date.strftime('%Y-%m-%d')
#                 week_key = email_date.strftime('%Y-W%U')  # Year-Week format
                
#                 daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
#                 weekly_counts[week_key] = weekly_counts.get(week_key, 0) + 1
                
#                 # Track senders over time
#                 sender_email = sender.split('<')[-1].replace('>', '') if '<' in sender else sender
#                 if week_key not in senders_over_time:
#                     senders_over_time[week_key] = {}
#                 senders_over_time[week_key][sender_email] = senders_over_time[week_key].get(sender_email, 0) + 1
                
#             except:
#                 day_key = "unknown"
#                 weekly_counts["unknown"] = weekly_counts.get("unknown", 0) + 1
            
#             # Extract keyword context
#             if keyword.lower() in content.lower():
#                 keyword_pos = content.lower().find(keyword.lower())
#                 start_pos = max(0, keyword_pos - 100)
#                 end_pos = min(len(content), keyword_pos + len(keyword) + 100)
#                 context = content[start_pos:end_pos]
                
#                 keyword_contexts.append({
#                     'date': day_key,
#                     'sender': sender,
#                     'subject': subject,
#                     'context': context
#                 })
        
#         # Generate trend analysis
#         ai_prompt = f"""
#         Analyze keyword "{keyword}" trends over {days_back} days:
        
#         Total emails found: {len(messages)}
#         Date range: {start_date_str} to {end_date_str}
        
#         Daily email counts with keyword:
#         {json.dumps(dict(sorted(daily_counts.items())), indent=2)}
        
#         Weekly email counts:
#         {json.dumps(dict(sorted(weekly_counts.items())), indent=2)}
        
#         Keyword contexts over time:
#         {json.dumps(keyword_contexts[:15], indent=2)}
        
#         Senders over time:
#         {json.dumps(senders_over_time, indent=2)}
        
#         Provide trend analysis:
#         1. Keyword usage frequency trends (increasing, decreasing, stable)
#         2. Peak periods for this keyword
#         3. Context evolution - how the keyword usage has changed
#         4. Sender patterns - who talks about this keyword and when
#         5. Seasonal or periodic patterns
#         6. Recent developments related to this keyword
#         7. Predictions and recommendations based on trends
#         8. Key time periods requiring attention
        
#         Trend Analysis:
#         """
        
#         analysis = llm_instance.invoke(ai_prompt)
        
#         # Store analysis in Firestore
#         analysis_doc = {
#             "keyword": keyword,
#             "days_analyzed": days_back,
#             "date_range": f"{start_date_str} to {end_date_str}",
#             "total_emails": len(messages),
#             "daily_counts": dict(sorted(daily_counts.items())),
#             "weekly_counts": dict(sorted(weekly_counts.items())),
#             "analysis": analysis,
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#             "type": "keyword_trend_analysis"
#         }
        
#         db.collection("email_analysis").document(f"trend_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}").set(analysis_doc)
        
#         return json.dumps({
#             "success": True,
#             "keyword": keyword,
#             "days_analyzed": days_back,
#             "date_range": f"{start_date_str} to {end_date_str}",
#             "total_emails": len(messages),
#             "daily_counts": dict(sorted(daily_counts.items())),
#             "weekly_counts": dict(sorted(weekly_counts.items())),
#             "peak_day": max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else None,
#             "analysis": analysis,
#             "stored_in_firestore": True
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error analyzing keyword trends: {str(e)}"
#         }, indent=2)

# def search_and_analyze_with_advanced_filters(
#     keyword: str, 
#     sender: str = None, 
#     date_after: str = None, 
#     date_before: str = None,
#     has_attachment: bool = None,
#     is_unread: bool = None,
#     max_results: int = 25
# ) -> str:
#     """Advanced email search and analysis with multiple filters"""
#     try:
#         ensure_services()
        
#         # Build advanced search query
#         query_parts = [keyword]
        
#         if sender:
#             query_parts.append(f"from:{sender}")
#         if date_after:
#             query_parts.append(f"after:{date_after}")
#         if date_before:
#             query_parts.append(f"before:{date_before}")
#         if has_attachment is True:
#             query_parts.append("has:attachment")
#         elif has_attachment is False:
#             query_parts.append("-has:attachment")
#         if is_unread is True:
#             query_parts.append("is:unread")
#         elif is_unread is False:
#             query_parts.append("-is:unread")
        
#         query = " ".join(query_parts)
        
#         result = gmail_service.users().messages().list(
#             userId="me",
#             q=query,
#             maxResults=max_results
#         ).execute()
        
#         messages = result.get('messages', [])
        
#         if not messages:
#             return json.dumps({
#                 "success": True,
#                 "search_query": query,
#                 "filters_applied": {
#                     "keyword": keyword,
#                     "sender": sender,
#                     "date_after": date_after,
#                     "date_before": date_before,
#                     "has_attachment": has_attachment,
#                     "is_unread": is_unread
#                 },
#                 "message": "No emails found matching the criteria",
#                 "analysis": "No analysis available"
#             }, indent=2)
        
#         # Analyze filtered emails
#         filtered_emails = []
#         attachment_count = 0
#         unread_count = 0
#         senders = {}
        
#         for msg in messages:
#             msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
#             headers = msg_detail['payload']['headers']
            
#             subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
#             sender_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
#             date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
#             content = get_email_content(msg_detail)
            
#             # Check for attachments
#             has_attachments = 'parts' in msg_detail['payload'] and any(
#                 part.get('filename') for part in msg_detail['payload']['parts']
#             )
#             if has_attachments:
#                 attachment_count += 1
            
#             # Check if unread
#             is_unread_msg = 'UNREAD' in msg_detail.get('labelIds', [])
#             if is_unread_msg:
#                 unread_count += 1
            
#             # Track senders
#             sender_clean = sender_email.split('<')[-1].replace('>', '') if '<' in sender_email else sender_email
#             senders[sender_clean] = senders.get(sender_clean, 0) + 1
            
#             # Extract keyword context
#             keyword_context = ""
#             if keyword.lower() in content.lower():
#                 keyword_pos = content.lower().find(keyword.lower())
#                 start_pos = max(0, keyword_pos - 100)
#                 end_pos = min(len(content), keyword_pos + len(keyword) + 100)
#                 keyword_context = content[start_pos:end_pos]
            
#             filtered_emails.append({
#                 'message_id': msg['id'],
#                 'subject': subject,
#                 'from': sender_email,
#                 'date': date,
#                 'has_attachments': has_attachments,
#                 'is_unread': is_unread_msg,
#                 'keyword_context': keyword_context,
#                 'content_preview': content[:250]
#             })
        
#         # Generate advanced analysis
#         top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5]
        
#         ai_prompt = f"""
#         Advanced filtered email analysis:
        
#         Search Query: {query}
#         Filters Applied:
#         - Keyword: {keyword}
#         - Sender: {sender or "Any"}
#         - After Date: {date_after or "Any"}
#         - Before Date: {date_before or "Any"}
#         - Has Attachment: {has_attachment if has_attachment is not None else "Any"}
#         - Is Unread: {is_unread if is_unread is not None else "Any"}
        
#         Results:
#         - Total emails found: {len(messages)}
#         - Emails with attachments: {attachment_count}
#         - Unread emails: {unread_count}
#         - Top senders: {top_senders}
        
#         Sample filtered emails:
#         {json.dumps(filtered_emails[:10], indent=2)}
        
#         Provide advanced filtered analysis:
#         1. Impact of applied filters on results
#         2. Patterns specific to these filtered emails
#         3. Key insights from the filtered dataset
#         4. Priority emails within filtered results
#         5. Action items from filtered emails
#         6. Recommendations for handling these filtered emails
#         7. Notable trends in the filtered data
#         8. Follow-up suggestions based on filter criteria
        
#         Advanced Analysis:
#         """
        
#         analysis = llm_instance.invoke(ai_prompt)
        
#         # Store analysis in Firestore
#         analysis_doc = {
#             "search_query": query,
#             "keyword": keyword,
#             "filters": {
#                 "sender": sender,
#                 "date_after": date_after,
#                 "date_before": date_before,
#                 "has_attachment": has_attachment,
#                 "is_unread": is_unread
#             },
#             "total_emails": len(messages),
#             "attachment_count": attachment_count,
#             "unread_count": unread_count,
#             "top_senders": dict(top_senders),
#             "analysis": analysis,
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#             "type": "advanced_filtered_analysis"
#         }
        
#         db.collection("email_analysis").document(f"filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}").set(analysis_doc)
        
#         return json.dumps({
#             "success": True,
#             "search_query": query,
#             "filters_applied": {
#                 "keyword": keyword,
#                 "sender": sender,
#                 "date_after": date_after,
#                 "date_before": date_before,
#                 "has_attachment": has_attachment,
#                 "is_unread": is_unread
#             },
#             "results_summary": {
#                 "total_emails": len(messages),
#                 "emails_with_attachments": attachment_count,
#                 "unread_emails": unread_count,
#                 "top_senders": dict(top_senders)
#             },
#             "analysis": analysis,
#             "stored_in_firestore": True
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error in advanced filtered analysis: {str(e)}"
#         }, indent=2)

# def get_stored_date_analyses(limit: int = 20) -> str:
#     """Get all stored daily email analyses from the database"""
#     try:
#         # Query Firestore for daily analyses
#         analyses_ref = db.collection("email_analysis").where("type", "==", "daily_analysis").order_by("date", direction=firestore.Query.DESCENDING).limit(limit)
#         docs = analyses_ref.stream()
        
#         stored_analyses = []
        
#         for doc in docs:
#             data = doc.to_dict()
#             stored_analyses.append({
#                 'document_id': doc.id,
#                 'date': data.get('date', 'Unknown'),
#                 'email_count': data.get('email_count', 0),
#                 'analyzed_emails': data.get('analyzed_emails', 0),
#                 'status': data.get('status', 'unknown'),
#                 'analyzed_on': data.get('timestamp', 'Unknown'),
#                 'top_senders': data.get('top_senders', {}),
#                 'has_analysis': bool(data.get('analysis', '').strip())
#             })
        
#         return json.dumps({
#             "success": True,
#             "total_stored_analyses": len(stored_analyses),
#             "limit_applied": limit,
#             "stored_analyses": stored_analyses,
#             "message": f"Retrieved {len(stored_analyses)} stored daily analyses from database"
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error retrieving stored analyses: {str(e)}"
#         }, indent=2)

# def refresh_date_analysis(date_str: str, force_refresh: bool = False) -> str:
#     """Refresh/update analysis for a specific date (useful when you want fresh analysis)"""
#     try:
#         ensure_services()
        
#         # Check if analysis exists
#         existing_doc = db.collection("email_analysis").document(f"daily_{date_str}").get()
        
#         if existing_doc.exists and not force_refresh:
#             existing_data = existing_doc.to_dict()
#             return json.dumps({
#                 "success": True,
#                 "date": date_str,
#                 "message": "Analysis already exists. Use force_refresh=True to override",
#                 "existing_analysis_date": existing_data.get("timestamp", "Unknown"),
#                 "email_count": existing_data.get("email_count", 0),
#                 "force_refresh_required": True
#             }, indent=2)
        
#         # Delete existing analysis if force refresh
#         if force_refresh and existing_doc.exists:
#             print(f"DEBUG: Force refreshing analysis for {date_str}")
#             db.collection("email_analysis").document(f"daily_{date_str}").delete()
        
#         # Perform fresh analysis (this will automatically store in database)
#         print(f"DEBUG: Performing fresh analysis for {date_str}")
#         fresh_analysis_result = get_email_analysis_by_date(date_str)
        
#         # Parse the result to add refresh context
#         result_data = json.loads(fresh_analysis_result)
#         if result_data.get("success"):
#             result_data["message"] = f"Analysis refreshed successfully for {date_str}"
#             result_data["refresh_timestamp"] = datetime.now(timezone.utc).isoformat()
#             result_data["was_forced_refresh"] = force_refresh
        
#         return json.dumps(result_data, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error refreshing date analysis: {str(e)}"
#         }, indent=2)

# def delete_date_analysis(date_str: str) -> str:
#     """Delete stored analysis for a specific date from database"""
#     try:
#         # Check if analysis exists
#         doc_ref = db.collection("email_analysis").document(f"daily_{date_str}")
#         existing_doc = doc_ref.get()
        
#         if not existing_doc.exists:
#             return json.dumps({
#                 "success": False,
#                 "date": date_str,
#                 "message": f"No analysis found for date {date_str} in database"
#             }, indent=2)
        
#         # Get existing data for confirmation
#         existing_data = existing_doc.to_dict()
        
#         # Delete the document
#         doc_ref.delete()
        
#         return json.dumps({
#             "success": True,
#             "date": date_str,
#             "message": f"Analysis for {date_str} deleted successfully from database",
#             "deleted_analysis_info": {
#                 "email_count": existing_data.get("email_count", 0),
#                 "analyzed_emails": existing_data.get("analyzed_emails", 0),
#                 "originally_analyzed_on": existing_data.get("timestamp", "Unknown")
#             }
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error deleting date analysis: {str(e)}"
#         }, indent=2)

# def analyze_previous_day_emails() -> str:
#     """Analyze all emails from the previous day with AI and store each email individually"""
#     try:
#         ensure_services()
        
#         # Get previous day in IST
#         ist = pytz.timezone('Asia/Kolkata')
#         now_ist = datetime.now(ist)
#         yesterday = now_ist - timedelta(days=1)
#         date_str = yesterday.strftime('%Y-%m-%d')
        
#         print(f"DEBUG: Starting daily analysis for {date_str} at {now_ist}")
        
#         # Search for emails from previous day
#         query = f"after:{date_str} before:{date_str}"
        
#         result = gmail_service.users().messages().list(
#             userId="me",
#             q=query,
#             maxResults=100  # Limit to avoid overwhelming processing
#         ).execute()
        
#         messages = result.get('messages', [])
        
#         if not messages:
#             # Store "no emails" result
#             no_emails_doc = {
#                 "date": date_str,
#                 "total_emails": 0,
#                 "analyzed_emails": 0,
#                 "emails": [],
#                 "analysis_summary": "No emails found for this date",
#                 "timestamp": datetime.now(timezone.utc).isoformat(),
#                 "type": "scheduled_daily_analysis",
#                 "status": "no_emails"
#             }
            
#             db.collection("daily_email_analysis").document(f"daily_{date_str}").set(no_emails_doc)
            
#             return json.dumps({
#                 "success": True,
#                 "date": date_str,
#                 "message": "No emails found for previous day",
#                 "total_emails": 0,
#                 "stored_in_firestore": True
#             }, indent=2)
        
#         print(f"DEBUG: Found {len(messages)} emails for {date_str}, starting AI analysis...")
        
#         # Analyze each email with AI
#         analyzed_emails = []
#         important_emails = []
#         categories = {}
        
#         for i, msg in enumerate(messages):
#             print(f"DEBUG: Analyzing email {i+1}/{len(messages)}")
            
#             try:
#                 # Get full message data
#                 msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
                
#                 # Perform AI analysis
#                 ai_analysis = analyze_email_with_ai(msg_detail)
                
#                 # Create standardized format
#                 standardized_analysis = create_standardized_email_analysis(msg['id'], msg_detail, ai_analysis)
                
#                 analyzed_emails.append(standardized_analysis)
                
#                 # Track important emails (score >= 7)
#                 importance_score = ai_analysis.get('classification', {}).get('importance_score', 0)
#                 if isinstance(importance_score, str):
#                     try:
#                         importance_score = int(importance_score)
#                     except:
#                         importance_score = 0
                
#                 if importance_score >= 7:
#                     important_emails.append({
#                         'messageId': msg['id'],
#                         'subject': standardized_analysis['email_info']['subject'],
#                         'from': standardized_analysis['email_info']['from'],
#                         'importance_score': importance_score,
#                         'category': ai_analysis.get('classification', {}).get('category', 'unknown')
#                     })
                
#                 # Track categories
#                 category = ai_analysis.get('classification', {}).get('category', 'unknown')
#                 categories[category] = categories.get(category, 0) + 1
                
#                 # Store individual email analysis
#                 db.collection("individual_email_analysis").document(f"email_{msg['id']}").set(standardized_analysis)
                
#             except Exception as e:
#                 print(f"DEBUG: Failed to analyze email {msg['id']}: {e}")
#                 continue
        
#         # Generate overall day summary with AI
#         summary_prompt = f"""
#         Analyze the following day's email summary for {date_str}:
        
#         Total emails: {len(messages)}
#         Successfully analyzed: {len(analyzed_emails)}
#         Important emails (score >= 7): {len(important_emails)}
        
#         Category breakdown:
#         {json.dumps(categories, indent=2)}
        
#         Important emails summary:
#         {json.dumps(important_emails[:10], indent=2)}
        
#         Provide a comprehensive daily summary including:
#         1. Overall communication volume trends
#         2. Most important emails and action items
#         3. Key categories and their significance
#         4. Recommendations for follow-up
#         5. Productivity insights for the day
        
#         Daily Summary:
#         """
        
#         daily_summary = llm_instance.invoke(summary_prompt)
        
#         # Store comprehensive daily analysis
#         daily_analysis_doc = {
#             "date": date_str,
#             "total_emails": len(messages),
#             "analyzed_emails": len(analyzed_emails),
#             "important_emails_count": len(important_emails),
#             "categories": categories,
#             "important_emails": important_emails,
#             "daily_summary": daily_summary,
#             "emails": [email['messageId'] for email in analyzed_emails],  # Reference to individual analyses
#             "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
#             "type": "scheduled_daily_analysis",
#             "status": "completed"
#         }
        
#         db.collection("daily_email_analysis").document(f"daily_{date_str}").set(daily_analysis_doc)
        
#         print(f"DEBUG: Daily analysis completed for {date_str}")
        
#         return json.dumps({
#             "success": True,
#             "date": date_str,
#             "message": "Daily analysis completed successfully",
#             "total_emails": len(messages),
#             "analyzed_emails": len(analyzed_emails),
#             "important_emails": len(important_emails),
#             "categories": categories,
#             "daily_summary": daily_summary,
#             "stored_in_firestore": True
#         }, indent=2)
        
#     except Exception as e:
#         error_msg = f"Error in daily analysis: {str(e)}"
#         print(f"DEBUG: {error_msg}")
        
#         # Store error in database for tracking
#         error_doc = {
#             "date": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
#             "error": error_msg,
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#             "type": "scheduled_daily_analysis",
#             "status": "error"
#         }
        
#         try:
#             db.collection("daily_email_analysis").document(f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}").set(error_doc)
#         except:
#             pass
        
#         return json.dumps({
#             "success": False,
#             "error": error_msg
#         }, indent=2)

# def get_individual_email_analysis(message_id: str) -> str:
#     """Get individual email analysis from database"""
#     try:
#         doc = db.collection("individual_email_analysis").document(f"email_{message_id}").get()
        
#         if not doc.exists:
#             return json.dumps({
#                 "success": False,
#                 "message_id": message_id,
#                 "error": "No analysis found for this email ID"
#             }, indent=2)
        
#         analysis_data = doc.to_dict()
        
#         return json.dumps({
#             "success": True,
#             "message_id": message_id,
#             "analysis": analysis_data
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error retrieving email analysis: {str(e)}"
#         }, indent=2)


# Global scheduler variables
# scheduler_thread = None
# scheduler_running = False

# def run_scheduler():
#     """Background scheduler function"""
#     global scheduler_running
    
#     print("DEBUG: Email analysis scheduler started")
    
#     while scheduler_running:
#         try:
#             schedule.run_pending()
#             time.sleep(60)  # Check every minute
#         except Exception as e:
#             print(f"DEBUG: Scheduler error: {e}")
#             time.sleep(300)  # Wait 5 minutes on error

# def start_daily_email_scheduler():
#     """Start the daily email analysis scheduler (12 AM IST)"""
#     global scheduler_thread, scheduler_running
    
#     if scheduler_running:
#         return json.dumps({
#             "success": False,
#             "message": "Scheduler is already running"
#         }, indent=2)
    
#     try:
#         # Schedule daily analysis at 12:00 AM IST
#         schedule.every().day.at("00:00").do(analyze_previous_day_emails)
        
#         scheduler_running = True
#         scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
#         scheduler_thread.start()
        
#         print("DEBUG: Daily email scheduler started - will run at 12:00 AM IST")
        
#         return json.dumps({
#             "success": True,
#             "message": "Daily email scheduler started successfully",
#             "schedule": "12:00 AM IST daily",
#             "status": "running"
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error starting scheduler: {str(e)}"
#         }, indent=2)

# def stop_daily_email_scheduler():
#     """Stop the daily email analysis scheduler"""
#     global scheduler_running
    
#     if not scheduler_running:
#         return json.dumps({
#             "success": False,
#             "message": "Scheduler is not running"
#         }, indent=2)
    
#     try:
#         scheduler_running = False
#         schedule.clear()
        
#         return json.dumps({
#             "success": True,
#             "message": "Daily email scheduler stopped successfully"
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error stopping scheduler: {str(e)}"
#         }, indent=2)

# def get_scheduler_status():
#     """Get current scheduler status"""
#     return json.dumps({
#         "success": True,
#         "scheduler_running": scheduler_running,
#         "scheduled_jobs": len(schedule.jobs),
#         "next_run": str(schedule.next_run()) if schedule.jobs else "No jobs scheduled"
#     }, indent=2)

# def manual_run_daily_analysis(date_str: str = None):
#     """Manually trigger daily analysis for a specific date"""
#     if date_str:
#         # Override the date in analyze_previous_day_emails
#         ist = pytz.timezone('Asia/Kolkata')
#         target_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=ist)
        
#         # Temporarily modify the function behavior
#         original_analyze = analyze_previous_day_emails
        
#         def analyze_specific_date():
#             # Custom analysis for specific date
#             try:
#                 ensure_services()
                
#                 print(f"DEBUG: Manual analysis for {date_str}")
                
#                 query = f"after:{date_str} before:{date_str}"
#                 result = gmail_service.users().messages().list(userId="me", q=query, maxResults=100).execute()
#                 messages = result.get('messages', [])
                
#                 if not messages:
#                     return json.dumps({"success": True, "date": date_str, "message": "No emails found", "total_emails": 0}, indent=2)
                
#                 # Same analysis logic as analyze_previous_day_emails but for specific date
#                 analyzed_emails = []
#                 important_emails = []
#                 categories = {}
                
#                 for i, msg in enumerate(messages):
#                     try:
#                         msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
#                         ai_analysis = analyze_email_with_ai(msg_detail)
#                         standardized_analysis = create_standardized_email_analysis(msg['id'], msg_detail, ai_analysis)
#                         analyzed_emails.append(standardized_analysis)
                        
#                         importance_score = ai_analysis.get('classification', {}).get('importance_score', 0)
#                         if isinstance(importance_score, str):
#                             try:
#                                 importance_score = int(importance_score)
#                             except:
#                                 importance_score = 0
                        
#                         if importance_score >= 7:
#                             important_emails.append({
#                                 'messageId': msg['id'],
#                                 'subject': standardized_analysis['email_info']['subject'],
#                                 'from': standardized_analysis['email_info']['from'],
#                                 'importance_score': importance_score,
#                                 'category': ai_analysis.get('classification', {}).get('category', 'unknown')
#                             })
                        
#                         category = ai_analysis.get('classification', {}).get('category', 'unknown')
#                         categories[category] = categories.get(category, 0) + 1
                        
#                         db.collection("individual_email_analysis").document(f"email_{msg['id']}").set(standardized_analysis)
                        
#                     except Exception as e:
#                         print(f"DEBUG: Failed to analyze email {msg['id']}: {e}")
#                         continue
                
#                 # Generate summary and store
#                 summary_prompt = f"Analyze emails for {date_str}: {len(analyzed_emails)} emails analyzed, {len(important_emails)} important. Categories: {categories}. Provide daily summary."
#                 daily_summary = llm_instance.invoke(summary_prompt)
                
#                 daily_analysis_doc = {
#                     "date": date_str,
#                     "total_emails": len(messages),
#                     "analyzed_emails": len(analyzed_emails),
#                     "important_emails_count": len(important_emails),
#                     "categories": categories,
#                     "important_emails": important_emails,
#                     "daily_summary": daily_summary,
#                     "emails": [email['messageId'] for email in analyzed_emails],
#                     "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
#                     "type": "manual_daily_analysis",
#                     "status": "completed"
#                 }
                
#                 db.collection("daily_email_analysis").document(f"daily_{date_str}").set(daily_analysis_doc)
                
#                 return json.dumps({
#                     "success": True,
#                     "date": date_str,
#                     "message": "Manual daily analysis completed",
#                     "total_emails": len(messages),
#                     "analyzed_emails": len(analyzed_emails),
#                     "important_emails": len(important_emails),
#                     "categories": categories,
#                     "stored_in_firestore": True
#                 }, indent=2)
                
#             except Exception as e:
#                 return json.dumps({"success": False, "error": f"Manual analysis error: {str(e)}"}, indent=2)
        
#         return analyze_specific_date()
#     else:
#         # Run for yesterday
#         return analyze_previous_day_emails()

# def test_standardized_analysis(message_id: str = None) -> str:
#     """Test the standardized analysis format with a sample email"""
#     try:
#         ensure_services()
        
#         if not message_id:
#             # Get a recent email for testing
#             result = gmail_service.users().messages().list(userId="me", maxResults=1).execute()
#             messages = result.get('messages', [])
#             if not messages:
#                 return json.dumps({"success": False, "error": "No emails found for testing"}, indent=2)
#             message_id = messages[0]['id']
        
#         # Get email data
#         msg_detail = gmail_service.users().messages().get(userId="me", id=message_id).execute()
        
#         # Perform AI analysis
#         ai_analysis = analyze_email_with_ai(msg_detail)
        
#         # Create standardized format
#         standardized_analysis = create_standardized_email_analysis(message_id, msg_detail, ai_analysis)
        
#         # Store in database
#         db.collection("individual_email_analysis").document(f"email_{message_id}").set(standardized_analysis)
        
#         return json.dumps({
#             "success": True,
#             "message": "Standardized analysis test completed",
#             "message_id": message_id,
#             "standardized_analysis": standardized_analysis,
#             "stored_in_firestore": True
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Test failed: {str(e)}"
#         }, indent=2)


# def manual_analyze_date_range(start_date: str, end_date: str, max_emails: int = 50) -> str:
#     """Manually analyze emails within a date range with AI insights"""
#     try:
#         ensure_services()
        
#         # Search for emails in date range
#         query = f"after:{start_date} before:{end_date}"
        
#         result = gmail_service.users().messages().list(
#             userId="me",
#             q=query,
#             maxResults=max_emails
#         ).execute()
        
#         messages = result.get('messages', [])
        
#         if not messages:
#             return json.dumps({
#                 "success": True,
#                 "date_range": f"{start_date} to {end_date}",
#                 "message": "No emails found in this date range",
#                 "analysis": "No analysis available"
#             }, indent=2)
        
#         # Categorize and analyze emails
#         email_data = []
#         senders = {}
#         subjects = []
        
#         for msg in messages:
#             msg_detail = gmail_service.users().messages().get(userId="me", id=msg['id']).execute()
#             headers = msg_detail['payload']['headers']
            
#             subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
#             sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
#             date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
#             content = get_email_content(msg_detail)
            
#             # Track senders
#             sender_email = sender.split('<')[-1].replace('>', '') if '<' in sender else sender
#             senders[sender_email] = senders.get(sender_email, 0) + 1
#             subjects.append(subject)
            
#             email_data.append({
#                 'message_id': msg['id'],
#                 'subject': subject,
#                 'from': sender,
#                 'date': date,
#                 'content_preview': content[:200]
#             })
        
#         # Generate comprehensive analysis
#         top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:10]
        
#         ai_prompt = f"""
#         Analyze emails from {start_date} to {end_date}:
        
#         Total emails: {len(messages)}
#         Top senders: {top_senders}
        
#         Sample emails:
#         {json.dumps(email_data[:10], indent=2)}
        
#         Provide comprehensive analysis:
#         1. Email volume trends
#         2. Most active correspondents
#         3. Common themes and topics
#         4. Important action items
#         5. Priority emails needing attention
#         6. Sentiment overview
#         7. Communication patterns
#         8. Recommendations for follow-up
        
#         Analysis:
#         """
        
#         analysis = llm_instance.invoke(ai_prompt)
        
#         # Store analysis in Firestore
#         analysis_doc = {
#             "start_date": start_date,
#             "end_date": end_date,
#             "email_count": len(messages),
#             "top_senders": dict(top_senders),
#             "analysis": analysis,
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#             "type": "range_analysis"
#         }
        
#         db.collection("email_analysis").document(f"range_{start_date}_to_{end_date}").set(analysis_doc)
        
#         return json.dumps({
#             "success": True,
#             "date_range": f"{start_date} to {end_date}",
#             "total_emails": len(messages),
#             "analyzed_emails": len(email_data),
#             "top_senders": dict(top_senders),
#             "analysis": analysis,
#             "stored_in_firestore": True
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error analyzing date range: {str(e)}"
#         }, indent=2)

# def get_analysis_stats() -> str:
#     """Get statistics about stored email analyses"""
#     try:
#         # Query Firestore for analysis statistics
#         analyses_ref = db.collection("email_analysis")
#         docs = analyses_ref.stream()
        
#         daily_analyses = 0
#         message_analyses = 0
#         range_analyses = 0
#         total_emails_analyzed = 0
        
#         recent_analyses = []
        
#         for doc in docs:
#             data = doc.to_dict()
#             analysis_type = data.get('type', 'unknown')
            
#             if analysis_type == 'daily_analysis':
#                 daily_analyses += 1
#                 total_emails_analyzed += data.get('email_count', 0)
#             elif analysis_type == 'message_analysis':
#                 message_analyses += 1
#                 total_emails_analyzed += 1
#             elif analysis_type == 'range_analysis':
#                 range_analyses += 1
#                 total_emails_analyzed += data.get('email_count', 0)
            
#             # Collect recent analyses
#             if len(recent_analyses) < 10:
#                 recent_analyses.append({
#                     'id': doc.id,
#                     'type': analysis_type,
#                     'timestamp': data.get('timestamp', 'Unknown'),
#                     'summary': data.get('date', data.get('message_id', data.get('date_range', 'Unknown')))
#                 })
        
#         return json.dumps({
#             "success": True,
#             "statistics": {
#                 "daily_analyses": daily_analyses,
#                 "message_analyses": message_analyses,
#                 "range_analyses": range_analyses,
#                 "total_analyses": daily_analyses + message_analyses + range_analyses,
#                 "total_emails_analyzed": total_emails_analyzed
#             },
#             "recent_analyses": recent_analyses,
#             "firestore_collection": "email_analysis"
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error getting analysis stats: {str(e)}"
#         }, indent=2)

# def send_email_with_attachment(to: str, subject: str, body: str, attachment_path: str) -> str:
#     """Send email with a single attachment"""
#     try:
#         ensure_services()
        
#         # Create message
#         message = MIMEMultipart()
#         message['to'] = to
#         message['subject'] = subject
#         message.attach(MIMEText(body, 'plain'))
        
#         # Add attachment
#         if os.path.exists(attachment_path):
#             with open(attachment_path, "rb") as attachment:
#                 part = MIMEBase('application', 'octet-stream')
#                 part.set_payload(attachment.read())
                
#             encoders.encode_base64(part)
#             filename = os.path.basename(attachment_path)
#             part.add_header(
#                 'Content-Disposition',
#                 f'attachment; filename= {filename}'
#             )
#             message.attach(part)
#         else:
#             return json.dumps({
#                 "success": False,
#                 "error": f"Attachment file not found: {attachment_path}"
#             }, indent=2)
        
#         raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
#         result = gmail_service.users().messages().send(
#             userId="me",
#             body={'raw': raw_message}
#         ).execute()
        
#         return json.dumps({
#             "success": True,
#             "message_id": result['id'],
#             "status": "Email with attachment sent successfully!",
#             "sent_to": to,
#             "attachment": filename
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error sending email with attachment: {str(e)}"
#         }, indent=2)

# def send_email_with_multiple_attachments(to: str, subject: str, body: str, attachment_paths: List[str]) -> str:
#     """Send email with multiple attachments"""
#     try:
#         ensure_services()
        
#         # Create message
#         message = MIMEMultipart()
#         message['to'] = to
#         message['subject'] = subject
#         message.attach(MIMEText(body, 'plain'))
        
#         attached_files = []
#         missing_files = []
        
#         # Add multiple attachments
#         for attachment_path in attachment_paths:
#             if os.path.exists(attachment_path):
#                 with open(attachment_path, "rb") as attachment:
#                     part = MIMEBase('application', 'octet-stream')
#                     part.set_payload(attachment.read())
                    
#                 encoders.encode_base64(part)
#                 filename = os.path.basename(attachment_path)
#                 part.add_header(
#                     'Content-Disposition',
#                     f'attachment; filename= {filename}'
#                 )
#                 message.attach(part)
#                 attached_files.append(filename)
#             else:
#                 missing_files.append(attachment_path)
        
#         # Check if any files were missing
#         if missing_files and not attached_files:
#             return json.dumps({
#                 "success": False,
#                 "error": f"No attachments found. Missing files: {missing_files}"
#             }, indent=2)
        
#         raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
#         result = gmail_service.users().messages().send(
#             userId="me",
#             body={'raw': raw_message}
#         ).execute()
        
#         response = {
#             "success": True,
#             "message_id": result['id'],
#             "status": "Email with attachments sent successfully!",
#             "sent_to": to,
#             "attached_files": attached_files
#         }
        
#         if missing_files:
#             response["warning"] = f"Some files were missing: {missing_files}"
        
#         return json.dumps(response, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error sending email with attachments: {str(e)}"
#         }, indent=2)

# def smart_reply_with_ai(message_id: str, user_instructions: str = "") -> str:
#     """Generate an AI-powered smart reply to an email based on its content using standardized analysis"""
#     try:
#         ensure_services()
        
#         # Get original message
#         original_msg = gmail_service.users().messages().get(userId="me", id=message_id).execute()
        
#         # First, analyze the email with our standardized AI analysis
#         ai_analysis = analyze_email_with_ai(original_msg)
#         standardized_analysis = create_standardized_email_analysis(message_id, original_msg, ai_analysis)
        
#         # Store the analysis for future reference
#         db.collection("individual_email_analysis").document(f"email_{message_id}").set(standardized_analysis)
        
#         # Extract email details
#         email_info = standardized_analysis['email_info']
#         classification = ai_analysis['classification']
        
#         # Create AI prompt for smart reply based on analysis
#         ai_prompt = f"""
#         You are an AI email assistant. Generate a professional reply based on this email analysis:
        
#         Original Email:
#         From: {email_info['from']}
#         Subject: {email_info['subject']}
#         Category: {classification['category']}
#         Importance: {classification['importance_score']}/10
#         Urgency: {classification['urgency']}
        
#         Analysis Summary: {ai_analysis['basic_info']['content_summary']}
#         Action Items: {ai_analysis['extracted_data']['action_items']}
        
#         {"User Instructions: " + user_instructions if user_instructions else ""}
        
#         Generate a reply that:
#         1. Acknowledges the email appropriately based on its importance and category
#         2. Addresses key action items if any
#         3. Matches the urgency level (professional for high urgency, friendly for low)
#         4. Is contextually appropriate for a tech student
        
#         Reply body only (no subject line):
#         """
        
#         # Generate AI reply
#         ai_reply = llm_instance.invoke(ai_prompt)
        
#         # Send the reply
#         reply_result = smart_reply_to_mail(message_id, ai_reply)
        
#         return json.dumps({
#             "success": True,
#             "message_id": message_id,
#             "ai_generated_reply": ai_reply,
#             "reply_result": json.loads(reply_result),
#             "email_analysis": standardized_analysis,
#             "stored_analysis": True
#         }, indent=2)
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error generating AI reply: {str(e)}"
#         }, indent=2)

# def create_standardized_email_analysis(message_id: str, email_data, ai_analysis: dict) -> dict:
#     """Create standardized email analysis format for storage"""
    
#     # Extract basic email info
#     headers = email_data["payload"]["headers"]
#     subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
#     sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
#     date_header = next((h["value"] for h in headers if h["name"] == "Date"), "No Date")
    
#     # Parse date to ISO format
#     try:
#         from email.utils import parsedate_to_datetime
#         parsed_date = parsedate_to_datetime(date_header)
#         iso_date = parsed_date.isoformat()
#         date_only = parsed_date.strftime('%Y-%m-%d')
#     except:
#         iso_date = datetime.now(timezone.utc).isoformat()
#         date_only = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
#     # Create standardized format
#     standardized_analysis = {
#         "messageId": message_id,
#         "date": date_only,
#         "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
#         "email_info": {
#             "from": sender,
#             "subject": subject,
#             "date_header": date_header,
#             "iso_date": iso_date,
#             "thread_id": email_data.get('threadId', ''),
#             "label_ids": email_data.get('labelIds', [])
#         },
#         "ai_analysis": ai_analysis,
#         "metadata": {
#             "analysis_version": "v2.0",
#             "tech_student_scoring": True,
#             "firestore_stored": True
#         }
#     }
    
#     return standardized_analysis


# def smart_reply_to_mail(message_id: str, reply_body: str, custom_subject: str = None) -> str:
#     """Send a simple reply to an email with your custom message and optional custom subject"""
#     try:
#         ensure_services()
        
#         # Get original message
#         original_msg = gmail_service.users().messages().get(userId="me", id=message_id).execute()
#         headers = original_msg['payload']['headers']
        
#         original_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
#         original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
#         message_id_header = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
        
#         # Get thread ID for proper threading
#         thread_id = original_msg.get('threadId', '')
        
#         # Create reply subject - use custom subject if provided, otherwise use "Re: original subject"
#         if custom_subject:
#             reply_subject = custom_subject
#         else:
#             reply_subject = original_subject if original_subject.startswith('Re: ') else f"Re: {original_subject}"
        
#         # Create and send reply message with proper threading
#         reply_message = MIMEText(reply_body)
#         reply_message['to'] = original_from
#         reply_message['subject'] = reply_subject
#         reply_message['In-Reply-To'] = message_id_header
#         reply_message['References'] = message_id_header
        
#         raw_message = base64.urlsafe_b64encode(reply_message.as_bytes()).decode()
        
#         # Send with threadId to ensure proper threading
#         send_body = {'raw': raw_message}
#         if thread_id:
#             send_body['threadId'] = thread_id
        
#         result = gmail_service.users().messages().send(
#             userId="me",
#             body=send_body
#         ).execute()
        
#         return json.dumps({
#             "success": True,
#             "message_id": result['id'],
#             "status": "Reply sent successfully!",
#             "reply_info": {
#                 "reply_body": reply_body,
#                 "reply_subject": reply_subject,
#                 "thread_id": thread_id
#             },
#             "original_email_info": {
#                 "from": original_from,
#                 "subject": original_subject,
#                 "message_id": message_id
#             },
#             "sent_to": original_from
#         }, indent=2)
            
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": f"Error sending reply: {str(e)}"
#         }, indent=2)
