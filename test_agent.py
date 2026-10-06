"""
==============================================================================
Intelligent Email Categorization Agent - Automated Unit & Integration Tests
Student Name : Aditya khiratkar
PRN          : 24070521071
Institute    : Symbiosis Institute of Technology, Nagpur
==============================================================================
Validates multi-class categorization accuracy, autonomous vs. gated tool
execution, and Human-In-The-Loop decision flows (Approve, Edit, Reject).
"""

import unittest
from langgraph.types import Command
from gmail_service import MockGmailService, DEFAULT_MOCK_EMAILS
from email_categorizer import EmailCategorizer
from agent import create_email_agent, run_with_approval


class TestIntelligentEmailAgent(unittest.TestCase):

    def setUp(self):
        """Set up fresh mock service and agent before each test."""
        self.mock_service = MockGmailService(DEFAULT_MOCK_EMAILS)
        self.agent, self.service = create_email_agent(gmail_service=self.mock_service)
        self.config = {"configurable": {"thread_id": "test_unit_thread_001"}}

    def test_multi_class_categorization(self):
        """Test categorization heuristic and priority rating for all sample emails."""
        categorized = EmailCategorizer.categorize_inbox(self.mock_service.emails)
        self.assertEqual(len(categorized), 6)

        categories = [e["classification"]["category"] for e in categorized]
        # Check that urgent, work, newsletter, promotions, spam categories exist
        self.assertTrue(any("Urgent" in c for c in categories), "Urgent category missing")
        self.assertTrue(any("Work" in c or "Academic" in c for c in categories), "Work category missing")
        self.assertTrue(any("Newsletter" in c for c in categories), "Newsletter category missing")
        self.assertTrue(any("Promotion" in c for c in categories), "Promotion category missing")
        self.assertTrue(any("Spam" in c or "Phishing" in c for c in categories), "Spam category missing")

        # Verify urgency scores
        urgent_email = next(e for e in categorized if e["id"] == "msg_001")
        self.assertEqual(urgent_email["classification"]["urgency_score"], 5)
        self.assertTrue(urgent_email["classification"]["action_required"])

        spam_email = next(e for e in categorized if e["id"] == "msg_006")
        self.assertEqual(spam_email["classification"]["urgency_score"], 1)
        self.assertFalse(spam_email["classification"]["action_required"])

    def test_autonomous_read_query(self):
        """Autonomous read-only query must complete without generating interrupts."""
        payload = {"messages": [{"role": "user", "content": "How many emails are in my inbox?"}]}
        result = self.agent.invoke(payload, config=self.config)

        self.assertFalse(
            bool(result.get("__interrupt__")),
            "Read-only query should NOT trigger a Human-In-The-Loop interrupt."
        )
        self.assertTrue(len(result["messages"]) >= 2)

    def test_gated_action_approval(self):
        """Sensitive send action must trigger interrupt and execute on approval."""
        payload = {"messages": [{"role": "user", "content": "Reply to Dr. Sharma confirming tomorrow's submission."}]}
        result = self.agent.invoke(payload, config=self.config)

        # Must trigger interrupt
        self.assertTrue(bool(result.get("__interrupt__")), "Sending email must trigger approval interrupt.")
        interrupt_val = result["__interrupt__"][0].value
        self.assertIn("action_requests", interrupt_val)
        self.assertEqual(interrupt_val["action_requests"][0]["name"], "send_gmail_message")

        # Resume with Approval
        resumed = self.agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=self.config)
        self.assertFalse(bool(resumed.get("__interrupt__")))
        # Check that message was recorded in sent messages of mock service
        self.assertEqual(len(self.mock_service.sent_messages), 1)
        self.assertEqual(self.mock_service.sent_messages[0]["to"], "dr.sharma@sitnagpur.edu.in")

    def test_gated_action_rejection(self):
        """Sensitive action must stop if human rejects with feedback."""
        payload = {"messages": [{"role": "user", "content": "Send reply to Dr. Sharma"}]}
        result = self.agent.invoke(payload, config=self.config)
        self.assertTrue(bool(result.get("__interrupt__")))

        # Resume with Rejection
        reason = "Rejected: Incorrect submission timing."
        resumed = self.agent.invoke(Command(resume={"decisions": [{"type": "reject", "message": reason}]}), config=self.config)
        self.assertFalse(bool(resumed.get("__interrupt__")))
        # Sent messages should remain 0
        self.assertEqual(len(self.mock_service.sent_messages), 0)

    def test_gated_action_edit(self):
        """Sensitive action must use human-edited arguments."""
        payload = {"messages": [{"role": "user", "content": "Reply to Dr. Sharma"}]}
        result = self.agent.invoke(payload, config=self.config)
        self.assertTrue(bool(result.get("__interrupt__")))

        # Resume with Edited arguments
        edited_decisions = [{
            "type": "edit",
            "edited_action": {
                "name": "send_gmail_message",
                "args": {
                    "to": "dr.sharma@sitnagpur.edu.in",
                    "subject": "MODIFIED: Submission Update by Aditya",
                    "message": "Submitting tomorrow by 2 PM sharp. Aditya khiratkar (PRN: 24070521071)."
                }
            }
        }]
        resumed = self.agent.invoke(Command(resume={"decisions": edited_decisions}), config=self.config)
        self.assertFalse(bool(resumed.get("__interrupt__")))
        self.assertEqual(len(self.mock_service.sent_messages), 1)
        self.assertEqual(self.mock_service.sent_messages[0]["subject"], "MODIFIED: Submission Update by Aditya")


if __name__ == "__main__":
    unittest.main()
