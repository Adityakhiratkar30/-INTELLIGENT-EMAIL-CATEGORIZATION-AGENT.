"""
==============================================================================
Intelligent Email Categorization Agent - Core LangChain/LangGraph Agent
Student Name : Aditya khiratkar
PRN          : 24070521071
Institute    : Symbiosis Institute of Technology, Nagpur
==============================================================================
Orchestrates email categorization, retrieval, draft preparation, and
human-in-the-loop (HITL) safety verification using LangChain create_agent
and LangGraph checkpointing.
"""

import os
from typing import Dict, Any, List, Optional, Callable
from dotenv import load_dotenv

# LangChain & LangGraph imports
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# Local service imports
from gmail_service import get_active_gmail_service, MockGmailService
from email_categorizer import EmailCategorizer

# Load environment configuration
load_dotenv()


# Policy defining which tool calls must interrupt execution for human review
SENSITIVE_TOOL_POLICY = {
    # Sending is irreversible -> always require human decision (approve, edit, or reject)
    "send_gmail_message": {
        "allowed_decisions": ["approve", "edit", "reject"],
    },
    # Drafts are reversible but gated so the agent cannot spam drafts without approval
    "create_gmail_draft": {
        "allowed_decisions": ["approve", "edit", "reject"],
    },
    # Deleting email is high risk -> always require human confirmation
    "delete_gmail_message": {
        "allowed_decisions": ["approve", "edit", "reject"],
    },
    # Read-only tools execute autonomously without interruption
    "search_gmail": False,
    "get_gmail_message": False,
    "get_gmail_thread": False,
    "categorize_emails": False,
}


def build_tools(gmail_service: Any) -> List[Any]:
    """
    Constructs LangChain tools bound to the active Gmail service (live or mock).
    """

    @tool
    def search_gmail(query: str = "") -> str:
        """Search Gmail inbox for emails matching a query keyword or return recent emails."""
        if isinstance(gmail_service, MockGmailService):
            results = gmail_service.search_emails(query=query)
        else:
            # Live Gmail API Resource
            try:
                res = gmail_service.users().messages().list(userId="me", q=query, maxResults=10).execute()
                msg_ids = res.get("messages", [])
                results = []
                for m in msg_ids:
                    msg = gmail_service.users().messages().get(userId="me", id=m["id"], format="snippet").execute()
                    results.append({
                        "id": msg["id"],
                        "threadId": msg.get("threadId"),
                        "snippet": msg.get("snippet", ""),
                        "labels": msg.get("labelIds", []),
                    })
            except Exception as e:
                return f"Error querying Gmail API: {e}"

        if not results:
            return "No matching emails found."

        summary = []
        for em in results:
            sender = em.get("sender", "Unknown")
            subject = em.get("subject", "No Subject")
            snippet = em.get("snippet", "")
            summary.append(f"• [ID: {em['id']}] From: {sender} | Subject: {subject}\n  Snippet: {snippet}")
        return "\n".join(summary)

    @tool
    def get_gmail_message(message_id: str) -> str:
        """Retrieve the complete content and metadata of a specific email by its message ID."""
        if isinstance(gmail_service, MockGmailService):
            msg = gmail_service.get_message(message_id)
        else:
            try:
                msg = gmail_service.users().messages().get(userId="me", id=message_id, format="full").execute()
            except Exception as e:
                return f"Error retrieving message: {e}"

        if not msg:
            return f"Message ID '{message_id}' not found."

        return (
            f"Message ID: {msg.get('id')}\n"
            f"Sender: {msg.get('sender')}\n"
            f"Recipient: {msg.get('recipient')}\n"
            f"Subject: {msg.get('subject')}\n"
            f"Date: {msg.get('date')}\n"
            f"Labels: {msg.get('labels')}\n"
            f"Content:\n{msg.get('body', msg.get('snippet', ''))}"
        )

    @tool
    def get_gmail_thread(thread_id: str) -> str:
        """Retrieve all email messages associated with a thread ID."""
        if isinstance(gmail_service, MockGmailService):
            thread_msgs = gmail_service.get_thread(thread_id)
        else:
            try:
                res = gmail_service.users().threads().get(userId="me", id=thread_id).execute()
                thread_msgs = res.get("messages", [])
            except Exception as e:
                return f"Error retrieving thread: {e}"

        if not thread_msgs:
            return f"Thread '{thread_id}' not found."

        out = [f"Thread {thread_id} ({len(thread_msgs)} messages):"]
        for m in thread_msgs:
            out.append(f"- [{m.get('id')}] {m.get('sender', 'Sender')}: {m.get('subject', 'Subject')}\n  {m.get('body', m.get('snippet', ''))}")
        return "\n\n".join(out)

    @tool
    def categorize_emails(query: str = "") -> str:
        """
        Scan inbox emails and classify them into categories:
        Urgent/Action Required, Work/Academic, Personal, Newsletters, Promotions, Spam/Phishing.
        """
        if isinstance(gmail_service, MockGmailService):
            emails = gmail_service.search_emails(query=query)
        else:
            emails = []
            try:
                res = gmail_service.users().messages().list(userId="me", q=query, maxResults=10).execute()
                for m in res.get("messages", []):
                    msg = gmail_service.users().messages().get(userId="me", id=m["id"], format="full").execute()
                    emails.append(msg)
            except Exception as e:
                return f"Error accessing emails for categorization: {e}"

        categorized = EmailCategorizer.categorize_inbox(emails)
        if not categorized:
            return "Inbox is empty or no emails found to categorize."

        report = ["=== INTELLIGENT INBOX CATEGORIZATION REPORT ==="]
        for em in categorized:
            cls = em["classification"]
            report.append(
                f"\n[{em['id']}] {cls['category']} (Urgency: {cls['urgency_score']}/5)\n"
                f"  From: {em.get('sender', 'Unknown')}\n"
                f"  Subject: {em.get('subject', 'No Subject')}\n"
                f"  Summary: {cls['summary']}\n"
                f"  Action Required: {'YES' if cls['action_required'] else 'NO'} -> {cls['suggested_action']}"
            )
        return "\n".join(report)

    @tool
    def create_gmail_draft(to: str, subject: str, message: str) -> str:
        """
        Create an email draft in Gmail.
        NOTE: This sensitive action triggers a Human-in-the-Loop review before creation.
        """
        if isinstance(gmail_service, MockGmailService):
            res = gmail_service.create_draft(to=to, subject=subject, message=message)
            return f"Draft created successfully. ID: {res['id']}. Saved in Drafts."
        else:
            try:
                # Live Gmail API draft creation
                import base64
                from email.mime.text import MIMEText
                mime = MIMEText(message)
                mime["to"] = to
                mime["subject"] = subject
                raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
                draft = gmail_service.users().drafts().create(
                    userId="me", body={"message": {"raw": raw}}
                ).execute()
                return f"Draft created on Gmail! Draft ID: {draft.get('id')}"
            except Exception as e:
                return f"Error creating draft in Gmail: {e}"

    @tool
    def send_gmail_message(to: str, subject: str, message: str) -> str:
        """
        Send an email message via Gmail.
        CRITICAL: Irreversible action. Gated by Human-in-the-Loop safety approval.
        """
        if isinstance(gmail_service, MockGmailService):
            res = gmail_service.send_message(to=to, subject=subject, message=message)
            return f"Email successfully sent to '{to}'. Message ID: {res['id']}."
        else:
            try:
                import base64
                from email.mime.text import MIMEText
                mime = MIMEText(message)
                mime["to"] = to
                mime["subject"] = subject
                raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
                sent = gmail_service.users().messages().send(
                    userId="me", body={"raw": raw}
                ).execute()
                return f"Email sent successfully via Gmail API! Message ID: {sent.get('id')}"
            except Exception as e:
                return f"Error sending email via Gmail API: {e}"

    @tool
    def delete_gmail_message(message_id: str) -> str:
        """
        Permanently delete an email message.
        CRITICAL: Gated by Human-in-the-Loop safety approval.
        """
        if isinstance(gmail_service, MockGmailService):
            res = gmail_service.delete_message(message_id)
            return res["message"]
        else:
            try:
                gmail_service.users().messages().delete(userId="me", id=message_id).execute()
                return f"Message {message_id} permanently deleted from Gmail."
            except Exception as e:
                return f"Error deleting email: {e}"

    return [
        search_gmail,
        get_gmail_message,
        get_gmail_thread,
        categorize_emails,
        create_gmail_draft,
        send_gmail_message,
        delete_gmail_message,
    ]


from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class MockToolCallingChatModel(BaseChatModel):
    """
    Offline tool-calling chat model. Enables full testing of categorization,
    tool invocation, and Human-in-the-Loop approval workflows without API keys.
    """

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        last = messages[-1]
        text = last.content if isinstance(last.content, str) else ""

        # If previous message was a Tool execution result
        if isinstance(last, ToolMessage):
            msg = AIMessage(content="Tool execution verified. Action successfully completed and recorded.")
        # If user asks to reply, send, or draft an email
        elif any(k in text.lower() for k in ["reply", "send", "draft", "write to", "email to"]):
            msg = AIMessage(
                content="I have drafted a confirmation email for Dr. Rajesh Sharma regarding the Capstone submission. Requesting human confirmation before sending.",
                tool_calls=[{
                    "name": "send_gmail_message",
                    "args": {
                        "to": "dr.sharma@sitnagpur.edu.in",
                        "subject": "Re: Capstone Project Phase-II Final Submission",
                        "message": (
                            "Respected Dr. Rajesh Sharma,\n\n"
                            "I confirm that my Capstone Project Phase-II code repository, documentation, "
                            "and demonstration recording are prepared and will be submitted before 5:00 PM tomorrow.\n\n"
                            "Warm regards,\n"
                            "Aditya khiratkar\n"
                            "PRN: 24070521071\n"
                            "Symbiosis Institute of Technology, Nagpur"
                        )
                    },
                    "id": "call_hitl_send_001"
                }]
            )
        # If user asks to delete an email
        elif "delete" in text.lower() or "spam" in text.lower() and "remove" in text.lower():
            msg = AIMessage(
                content="Preparing to delete suspicious phishing message (ID: msg_006). Requesting approval.",
                tool_calls=[{
                    "name": "delete_gmail_message",
                    "args": {"message_id": "msg_006"},
                    "id": "call_hitl_delete_001"
                }]
            )
        # Default read-only / categorization query
        else:
            msg = AIMessage(
                content=(
                    "📬 Inbox Analysis Complete:\n"
                    "• Total Emails Analyzed: 6\n"
                    "• 🚨 Urgent / Action Required (2): Capstone Project Submission Deadline & AWS Cloud Billing Alert\n"
                    "• 💼 Work / Academic (1): Google Technical Interview Invitation (SWE Intern 2027)\n"
                    "• 📢 Newsletters (1): LangChain Multi-Agent HITL Weekly\n"
                    "• 🛍️ Promotions (1): Flipkart Tech Sale\n"
                    "• 🗑️ Spam / Phishing (1): Lottery Cash Prize Scam\n\n"
                    "Recommended Action: Reply to Google recruiting with interview availability, and review AWS console."
                )
            )

        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools: Any, **kwargs: Any):
        return self

    @property
    def _llm_type(self) -> str:
        return "mock-tool-calling-chat"


def get_llm():
    """
    Initializes ChatOpenAI model or graceful fallback model.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

    if api_key and not api_key.startswith("your_openai"):
        return ChatOpenAI(model=model_name, temperature=0, api_key=api_key)

    print("[Agent] Notice: No active OPENAI_API_KEY detected. Using Offline Demonstration LLM.")
    return MockToolCallingChatModel()



def create_email_agent(gmail_service: Optional[Any] = None):
    """
    Factory creating the Intelligent Email Categorization Agent with LangChain & LangGraph.
    Configured with HumanInTheLoopMiddleware and InMemorySaver checkpointer.
    """
    service = gmail_service or get_active_gmail_service()
    tools = build_tools(service)

    hitl_middleware = HumanInTheLoopMiddleware(
        interrupt_on=SENSITIVE_TOOL_POLICY,
        description_prefix="Tool execution pending human approval",
    )

    instructions = (
        "You are the Intelligent Email Categorization Agent created by Aditya khiratkar (PRN: 24070521071).\n"
        "Your mission is to triage user emails, sort them into structured categories (Urgent, Work/Academic, "
        "Personal, Newsletters, Promotions, Spam), and draft high-quality contextual replies.\n\n"
        "SAFETY POLICY:\n"
        "- Read-only actions (searching, getting messages, categorizing) execute autonomously.\n"
        "- High-stakes actions (sending email, creating drafts, deleting messages) will ALWAYS pause "
        "  for human-in-the-loop decision (approve, edit, or reject).\n"
        "- Feel free to prepare send or draft actions when appropriate, because a human will review "
        "  and confirm the details before anything leaves the inbox."
    )

    checkpointer = InMemorySaver()
    llm = get_llm()

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=instructions,
        middleware=[hitl_middleware],
        checkpointer=checkpointer,
    )
    return agent, service


def describe_action_request(request: Dict[str, Any]) -> None:
    """Pretty-print a pending tool call for human review."""
    action = request.get("action_request", {})
    action_name = action.get("name") or action.get("action")
    allowed = request.get("config", {}).get("allowed_decisions", ["approve", "edit", "reject"])
    print(f"\n========================================================")
    print(f"🛑 HUMAN-IN-THE-LOOP SAFETY GATE: ACTION APPROVAL NEEDED")
    print(f"========================================================")
    print(f"Proposed Action : {action_name}")
    print(f"Target Details  :")
    for k, v in action.get("args", {}).items():
        val_str = str(v).replace("\n", "\n    ")
        print(f"  • {k}: {val_str}")
    print(f"Allowed Choices : {allowed}")
    print(f"========================================================")


def ask_human_for_decision(
    request: Dict[str, Any], input_fn: Optional[Callable[[str], str]] = None
) -> Dict[str, Any]:
    """
    Collects a decision from the human operator: approve, edit, or reject.
    """
    describe_action_request(request)
    _input = input_fn or input

    choice = _input("Decision [approve / edit / reject]: ").strip().lower()

    if choice == "approve":
        print("✅ Decision: APPROVED. Executing action...")
        return {"type": "approve"}

    elif choice == "reject":
        reason = _input("Reason for rejecting (will be provided to agent): ").strip()
        print(f"❌ Decision: REJECTED. Reason: '{reason}'")
        return {"type": "reject", "message": reason or "Action rejected by user."}

    elif choice == "edit":
        action = request.get("action_request", {})
        action_name = action.get("name") or action.get("action")
        edited_args = dict(action.get("args", {}))
        print("✏️ Mode: EDIT ARGUMENTS (press Enter to keep existing value):")
        for k, current_val in edited_args.items():
            new_val = _input(f"  New value for '{k}' [current: {current_val}]: ").strip()
            if new_val:
                edited_args[k] = new_val
        print(f"📝 Decision: EDITED. Updated arguments: {edited_args}")
        return {
            "type": "edit",
            "edited_action": {"name": action_name, "args": edited_args},
        }

    else:
        print("⚠️ Unrecognized input, defaulting to REJECT for safety.")
        return {"type": "reject", "message": "Unrecognized decision input; rejected for security."}


def run_with_approval(
    agent: Any,
    payload: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
    decision_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Any:
    """
    Invoke the agent and resume through Human-In-The-Loop interrupts until completion.
    """
    if config is None:
        config = {"configurable": {"thread_id": "email_agent_session_1"}}

    handler = decision_handler or ask_human_for_decision
    result = agent.invoke(payload, config=config)

    while result.get("__interrupt__"):
        interrupt_info = result["__interrupt__"][0]
        val = interrupt_info.value

        # Normalize value to a list of request dictionaries
        requests_to_process = []
        if isinstance(val, dict) and "action_requests" in val:
            action_requests = val.get("action_requests", [])
            review_configs = val.get("review_configs", [])
            for idx, act in enumerate(action_requests):
                cfg = review_configs[idx] if idx < len(review_configs) else {}
                requests_to_process.append({"action_request": act, "config": cfg})
        elif isinstance(val, list):
            requests_to_process = val
        else:
            requests_to_process = [{"action_request": val, "config": {}}]

        # Collect decision for each pending action request
        decisions = [handler(req) for req in requests_to_process]

        # Resume agent with decisions
        result = agent.invoke(Command(resume={"decisions": decisions}), config=config)

    return result
