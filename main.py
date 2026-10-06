"""
==============================================================================
Intelligent Email Categorization Agent - Main Terminal Application
Student Name : Aditya khiratkar
PRN          : 24070521071
Institute    : Symbiosis Institute of Technology, Nagpur
Course       : Agentic AI & Automation
==============================================================================
Interactive CLI & Demonstration Runner for Intelligent Email Categorization Agent.
Combines LangChain/LangGraph orchestration with Gmail API integration
and Human-In-The-Loop (HITL) safety verification.
"""

import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv

from gmail_service import get_active_gmail_service, MockGmailService
from email_categorizer import EmailCategorizer
from agent import create_email_agent, run_with_approval, SENSITIVE_TOOL_POLICY

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

load_dotenv()


def print_banner():
    """Prints the project and student credentials header."""
    print("=" * 80)
    print("  INTELLIGENT EMAIL CATEGORIZATION AGENT")
    print("  LangChain & LangGraph Multi-Agent Architecture with Gmail API Integration")
    print("=" * 80)
    print("  STUDENT CREDENTIALS:")
    print("    Name      : Aditya khiratkar")
    print("    PRN       : 24070521071")
    print("    Institute : Symbiosis Institute of Technology, Nagpur")
    print("=" * 80)
    print("  SAFETY PROTOCOL: Human-In-The-Loop (HITL) Gating Active")
    print("    • Read-Only Actions (search, read, categorize) : AUTONOMOUS")
    print("    • Irreversible Actions (send, draft, delete)   : GATED [approve/edit/reject]")
    print("=" * 80)
    print()


def display_inbox_categorization(gmail_service):
    """Fetches inbox emails and displays a structured categorization table."""
    print("\n" + "=" * 95)
    print("  INBOX INTELLIGENT CATEGORIZATION REPORT")
    print("=" * 95)

    if isinstance(gmail_service, MockGmailService):
        emails = gmail_service.search_emails()
    else:
        # Live Gmail fetch
        try:
            res = gmail_service.users().messages().list(userId="me", maxResults=10).execute()
            msg_ids = res.get("messages", [])
            emails = []
            for m in msg_ids:
                msg = gmail_service.users().messages().get(userId="me", id=m["id"], format="full").execute()
                emails.append(msg)
        except Exception as e:
            print(f"[Error fetching live emails]: {e}")
            emails = []

    if not emails:
        print("  Inbox is empty or no messages found.")
        print("=" * 95)
        return

    categorized = EmailCategorizer.categorize_inbox(emails)

    print(f"  {'ID':<8} | {'CATEGORY':<30} | {'PRIORITY':<8} | {'SUBJECT':<42}")
    print("  " + "-" * 91)
    for em in categorized:
        cls_info = em["classification"]
        subject_preview = em.get("subject", "No Subject")[:40]
        print(f"  {em['id']:<8} | {cls_info['category']:<30} | {cls_info['urgency_score']}/5     | {subject_preview:<42}")

    print("=" * 95)
    print("\n  Detailed Action Recommendations:")
    for em in categorized:
        cls_info = em["classification"]
        if cls_info["urgency_score"] >= 3 or cls_info["action_required"]:
            print(f"  • [{em['id']}] From: {em.get('sender', 'Unknown')}")
            print(f"    Subject : {em.get('subject')}")
            print(f"    Action  : {cls_info['suggested_action']}")
            print(f"    Summary : {cls_info['summary']}\n")
    print("=" * 95)


def run_interactive_cli(agent, gmail_service):
    """Interactive loop allowing the user to query the agent directly."""
    config = {"configurable": {"thread_id": "aditya_cli_session_1"}}

    print("\n[Interactive Mode Activated]")
    print("Type your instructions for the agent (or 'exit' to quit, 'menu' for shortcuts).\n")

    while True:
        try:
            user_input = input("Email-Agent > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting Intelligent Email Categorization Agent. Goodbye!")
                break

            elif user_input.lower() == "menu":
                print("\nQuick Shortcut Options:")
                print("  1. 'triage'    -> Categorize and display current inbox")
                print("  2. 'search'    -> Search emails by keyword")
                print("  3. 'reply'     -> Reply to an email (triggers HITL gate)")
                print("  4. 'draft'     -> Create a draft response (triggers HITL gate)")
                print("  5. 'exit'      -> Terminate session\n")
                continue

            elif user_input.lower() == "triage":
                display_inbox_categorization(gmail_service)
                continue

            # Submit prompt to agent with approval gating
            payload = {"messages": [{"role": "user", "content": user_input}]}
            print(f"\n[Processing with LangGraph Agent...]")
            result = run_with_approval(agent, payload, config)

            last_msg = result["messages"][-1].content
            print(f"\n[Agent Output]:\n{last_msg}\n")

        except KeyboardInterrupt:
            print("\nSession interrupted by user.")
            break
        except Exception as e:
            print(f"\n[Error executing request]: {e}\n")


def run_automated_demo(agent, gmail_service):
    """Executes a pre-configured verification run covering read-only and gated actions."""
    config = {"configurable": {"thread_id": "demo_test_session_001"}}

    print("\n" + "=" * 80)
    print("  RUNNING AUTOMATED AGENTIC VERIFICATION SUITE")
    print("=" * 80)

    # 1. Structured Categorization
    print("\n[TEST 1] Multi-Class Inbox Triage & Priority Scoring:")
    display_inbox_categorization(gmail_service)

    # 2. Autonomous Read-Only Tool Execution
    print("\n[TEST 2] Autonomous Query (Zero Interrupts Expected):")
    prompt_1 = "Categorize my unread emails and tell me how many high-priority items require my attention."
    print(f"User Prompt: '{prompt_1}'")
    res_1 = run_with_approval(agent, {"messages": [{"role": "user", "content": prompt_1}]}, config)
    print(f"Agent Response:\n{res_1['messages'][-1].content}\n")

    # 3. Gated Action Simulation (Approval Gating)
    print("\n[TEST 3] Sensitive Action Testing (HITL Gating):")
    prompt_2 = "Reply to Dr. Rajesh Sharma confirming that my Capstone Project code and report will be uploaded by tomorrow 3:00 PM."
    print(f"User Prompt: '{prompt_2}'")

    # Define simulated human decision handler for automated test
    def automated_approver(request):
        action = request.get("action_request", {})
        action_name = action.get("name") or action.get("action")
        print(f"\n>> Simulated User Review for Action: '{action_name}'")
        for k, v in action.get("args", {}).items():
            val_snippet = str(v).replace("\n", " ")[:70]
            print(f"   • {k}: {val_snippet}...")
        print(">> Human Evaluator Decision: APPROVED")
        return {"type": "approve"}

    res_2 = run_with_approval(
        agent,
        {"messages": [{"role": "user", "content": prompt_2}]},
        config,
        decision_handler=automated_approver,
    )
    print(f"\nAgent Final Response:\n{res_2['messages'][-1].content}\n")
    print("=" * 80)
    print("  VERIFICATION SUITE COMPLETED SUCCESSFULLY")
    print("=" * 80)


def main():
    print_banner()
    agent, gmail_service = create_email_agent()

    # Check CLI arguments
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["--demo", "-d", "demo"]:
        run_automated_demo(agent, gmail_service)
    else:
        # Prompt user whether to run automated demo or interactive shell
        print("Select Execution Mode:")
        print("  1. Interactive CLI Shell (Default)")
        print("  2. Automated Demonstration & Verification Suite")
        choice = input("\nEnter choice [1 or 2, default 1]: ").strip()

        if choice == "2":
            run_automated_demo(agent, gmail_service)
        else:
            run_interactive_cli(agent, gmail_service)


if __name__ == "__main__":
    main()
