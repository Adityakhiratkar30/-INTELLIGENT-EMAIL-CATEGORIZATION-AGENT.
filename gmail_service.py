"""
==============================================================================
Intelligent Email Categorization Agent - Gmail Service Layer
Student Name : Aditya khiratkar
PRN          : 24070521071
Institute    : Symbiosis Institute of Technology, Nagpur
==============================================================================
Provides OAuth2 authentication and API operations for Gmail. Supports both
live Google Cloud Gmail API integration and an interactive Mock Mailbox sandbox
for offline testing and evaluation.
"""

import os
import json
import base64
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText

# Google API client imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build, Resource
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False


# Default Gmail Scopes (full read, send, draft, delete capabilities)
SCOPES = ["https://mail.google.com/"]

# Realistic initial emails for sandbox simulation & demonstration
DEFAULT_MOCK_EMAILS = [
    {
        "id": "msg_001",
        "threadId": "thread_001",
        "sender": "dr.sharma@sitnagpur.edu.in",
        "recipient": "aditya.khiratkar@sitnagpur.edu.in",
        "subject": "URGENT: Capstone Project Phase-II Final Submission Deadline",
        "date": "2026-10-05 09:30:00",
        "snippet": "Dear Aditya, please ensure your Agentic AI project report and code repository are submitted by tomorrow 5:00 PM...",
        "body": (
            "Dear Aditya khiratkar (PRN: 24070521071),\n\n"
            "This is a gentle reminder that the submission portal for Capstone Project Phase-II "
            "will strictly close tomorrow at 5:00 PM IST. Please upload your complete code repository, "
            "architecture documentation, and the final demonstration recording.\n\n"
            "Late submissions will incur a 15% grade deduction.\n\n"
            "Best regards,\n"
            "Dr. Rajesh Sharma\n"
            "Department of Computer Science & Engineering\n"
            "Symbiosis Institute of Technology, Nagpur"
        ),
        "labels": ["INBOX", "UNREAD", "IMPORTANT"],
    },
    {
        "id": "msg_002",
        "threadId": "thread_002",
        "sender": "university-talent@google.com",
        "recipient": "aditya.khiratkar@sitnagpur.edu.in",
        "subject": "Google Technical Interview Invitation - Software Engineer Intern (2027)",
        "date": "2026-10-05 11:15:00",
        "snippet": "Congratulations! We were impressed with your application and would like to schedule a technical round...",
        "body": (
            "Hi Aditya,\n\n"
            "Thank you for applying to the Software Engineer Intern role at Google. "
            "We were very impressed by your background in Agentic AI and LLM Orchestration.\n\n"
            "We would like to invite you for a 45-minute virtual technical interview. "
            "Please reply with your availability across the upcoming two weeks (Monday to Thursday, 10 AM - 4 PM IST).\n\n"
            "Warm regards,\n"
            "Google University Programs Team"
        ),
        "labels": ["INBOX", "UNREAD", "STARRED"],
    },
    {
        "id": "msg_003",
        "threadId": "thread_003",
        "sender": "no-reply@aws.amazon.com",
        "recipient": "aditya.khiratkar@sitnagpur.edu.in",
        "subject": "CRITICAL ALERT: AWS Cloud Billing Alert Exceeded (Account #9283-4819)",
        "date": "2026-10-05 14:00:00",
        "snippet": "Your AWS estimated monthly charges have exceeded your custom budget alarm of $50.00...",
        "body": (
            "Dear AWS Customer,\n\n"
            "Your account #9283-4819 has triggered a CloudWatch billing alarm. "
            "Current accrued charges for October 2026 stand at $78.40, which exceeds your threshold limit of $50.00.\n"
            "Primary drivers: EC2 GPU instances and S3 storage.\n\n"
            "Please review active resources in the AWS Management Console to avoid additional charges.\n\n"
            "Amazon Web Services"
        ),
        "labels": ["INBOX", "UNREAD"],
    },
    {
        "id": "msg_004",
        "threadId": "thread_004",
        "sender": "newsletter@langchain.dev",
        "recipient": "aditya.khiratkar@sitnagpur.edu.in",
        "subject": "LangChain Weekly: Multi-Agent HITL Patterns & LangGraph 2.0 Features",
        "date": "2026-10-04 18:00:00",
        "snippet": "Explore new Human-In-The-Loop patterns, memory checkpointing, and agent governance best practices...",
        "body": (
            "Hey LangChain builders,\n\n"
            "In this edition:\n"
            "- Implementing Human-In-The-Loop (HITL) middleware to gate high-risk actions\n"
            "- Combining LangGraph with Gmail and Slack APIs safely\n"
            "- Optimizing token efficiency for structured tool calling\n\n"
            "Read the full issue on our blog!\n\n"
            "The LangChain Team"
        ),
        "labels": ["INBOX", "NEWSLETTER"],
    },
    {
        "id": "msg_005",
        "threadId": "thread_005",
        "sender": "deals@promotions.flipkart.com",
        "recipient": "aditya.khiratkar@sitnagpur.edu.in",
        "subject": "Mega Tech Festive Sale: Up to 50% Off Developer Laptops, Keyboards & SSDs!",
        "date": "2026-10-04 10:20:00",
        "snippet": "Exclusive early access starts now! Check out top deals on MacBook, RTX gaming rigs and peripherals...",
        "body": (
            "Hi Aditya,\n\n"
            "The biggest tech sale of the season is live! Save up to 50% on top tech hardware, "
            "mechanical keyboards, ultra-wide monitors, and high-speed NVMe storage. "
            "Click here to claim your exclusive member discounts today only.\n\n"
            "Happy Shopping,\n"
            "The Flipkart Promotions Team"
        ),
        "labels": ["INBOX", "PROMOTIONS"],
    },
    {
        "id": "msg_006",
        "threadId": "thread_006",
        "sender": "winner-claim@intl-lottery-rewards-winner.org",
        "recipient": "aditya.khiratkar@sitnagpur.edu.in",
        "subject": "CLAIM PENDING: You have won $1,500,000 USD International Cash Prize!",
        "date": "2026-10-03 23:45:00",
        "snippet": "Attention beneficiary, your email won the annual Global Lucky Draw. Reply immediately with passport...",
        "body": (
            "ATTENTION BENEFICIARY,\n\n"
            "Your email address has been selected as the grand winner of $1,500,000.00 USD in our "
            "annual international sweepstakes. To release your payout immediately, reply to this email "
            "with your full banking credentials, birth certificate, and SSN.\n\n"
            "Failure to reply in 24 hours will forfeit your claim.\n\n"
            "Chief Treasury Officer"
        ),
        "labels": ["SPAM", "UNREAD"],
    },
]


class MockGmailService:
    """
    In-memory simulated Gmail API Service.
    Emulates Google Gmail API v1 operations for offline development,
    demonstration, and grading without external credentials.
    """

    def __init__(self, initial_emails: Optional[List[Dict[str, Any]]] = None):
        self.emails: List[Dict[str, Any]] = [dict(e) for e in (initial_emails or DEFAULT_MOCK_EMAILS)]
        self.drafts: List[Dict[str, Any]] = []
        self.sent_messages: List[Dict[str, Any]] = []
        self.deleted_message_ids: List[str] = []

    def search_emails(self, query: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        """Filter emails matching query keyword or return recent emails."""
        results = []
        q = query.lower().strip()
        for email in self.emails:
            if email["id"] in self.deleted_message_ids:
                continue
            if not q:
                results.append(email)
            else:
                combined_text = (
                    email["subject"] + " " + email["snippet"] + " " + email["sender"] + " " + " ".join(email.get("labels", []))
                ).lower()
                if q in combined_text or any(token in combined_text for token in q.split()):
                    results.append(email)
            if len(results) >= max_results:
                break
        return results

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of an email by ID."""
        for email in self.emails:
            if email["id"] == message_id:
                return dict(email)
        return None

    def get_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Retrieve all messages belonging to a thread."""
        return [dict(e) for e in self.emails if e.get("threadId") == thread_id and e["id"] not in self.deleted_message_ids]

    def create_draft(self, to: str, subject: str, message: str) -> Dict[str, Any]:
        """Create and store a draft email."""
        draft_id = f"draft_{len(self.drafts) + 1:03d}"
        draft_data = {
            "id": draft_id,
            "to": to,
            "subject": subject,
            "body": message,
            "status": "DRAFT",
            "created_at": "Just now",
        }
        self.drafts.append(draft_data)
        return {"id": draft_id, "message": f"Draft created successfully for '{to}' with ID '{draft_id}'."}

    def send_message(self, to: str, subject: str, message: str) -> Dict[str, Any]:
        """Send an email (irreversible sensitive action)."""
        msg_id = f"sent_{len(self.sent_messages) + 1:03d}"
        sent_record = {
            "id": msg_id,
            "to": to,
            "subject": subject,
            "body": message,
            "status": "SENT",
            "sent_at": "Just now",
        }
        self.sent_messages.append(sent_record)
        return {"id": msg_id, "status": "SENT", "message": f"Email successfully dispatched to '{to}'."}

    def delete_message(self, message_id: str) -> Dict[str, Any]:
        """Delete an email message by ID."""
        for email in self.emails:
            if email["id"] == message_id:
                self.deleted_message_ids.append(message_id)
                return {"id": message_id, "status": "DELETED", "message": f"Message {message_id} successfully deleted."}
        return {"id": message_id, "status": "NOT_FOUND", "message": f"Message {message_id} not found."}


def get_gmail_credentials(
    token_file: str = "token.json",
    client_secrets_file: str = "credentials.json",
    scopes: Optional[List[str]] = None,
) -> Optional[Any]:
    """
    Authenticate and return Google OAuth2 credentials.
    Reads cached token from token_file or triggers local browser consent flow.
    """
    if not GMAIL_API_AVAILABLE:
        print("[GmailService] Google API libraries not installed. Falling back to Mock service.")
        return None

    scopes = scopes or SCOPES
    creds = None

    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, scopes)
        except Exception as e:
            print(f"[GmailService] Warning: Could not load token file ({e}).")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[GmailService] Token refresh failed ({e}), re-authenticating...")
                creds = None

        if not creds:
            if not os.path.exists(client_secrets_file):
                print(f"[GmailService] Note: '{client_secrets_file}' not found. Live Gmail unavailable.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
            creds = flow.run_local_server(port=0)

        # Save credentials for future runs
        try:
            with open(token_file, "w") as token:
                token.write(creds.to_json())
            print(f"[GmailService] Token saved to {token_file}")
        except Exception as e:
            print(f"[GmailService] Warning: Could not save token file: {e}")

    return creds


def build_resource_service(credentials: Any) -> Optional[Any]:
    """Builds and returns the live Google API Resource Service for Gmail."""
    if not credentials or not GMAIL_API_AVAILABLE:
        return None
    try:
        return build("gmail", "v1", credentials=credentials)
    except Exception as e:
        print(f"[GmailService] Error building Gmail resource service: {e}")
        return None


def get_active_gmail_service(mode: str = "auto") -> Any:
    """
    Helper function to initialize the preferred Gmail service:
    - 'live': Forces live Gmail API (requires credentials.json)
    - 'mock': Forces in-memory Mock service
    - 'auto': Attempts live authentication; falls back gracefully to Mock
    """
    env_mode = os.getenv("EMAIL_AGENT_MODE", "auto").lower()
    selected_mode = mode if mode != "auto" else env_mode

    if selected_mode == "mock":
        print("[GmailService] Running in Sandbox Mock Mode (Safe simulated environment).")
        return MockGmailService()

    creds = get_gmail_credentials()
    if creds:
        service = build_resource_service(creds)
        if service:
            print("[GmailService] Connected to LIVE Gmail API successfully.")
            return service

    print("[GmailService] Using Sandbox Mock Mode (Default fallback).")
    return MockGmailService()
