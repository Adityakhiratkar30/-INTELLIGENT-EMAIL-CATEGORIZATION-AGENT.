"""
==============================================================================
Intelligent Email Categorization Agent - Email Categorization Engine
Student Name : Aditya khiratkar
PRN          : 24070521071
Institute    : Symbiosis Institute of Technology, Nagpur
==============================================================================
Provides structured classification, priority scoring, action extraction,
and sentiment assessment for incoming emails.
"""

import re
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class EmailClassification(BaseModel):
    """Structured classification output schema."""
    category: str = Field(
        description="Category: Urgent / Action Required, Work / Academic, Personal, Newsletters, Promotions, Spam / Phishing"
    )
    urgency_score: int = Field(
        description="Priority urgency level from 1 (lowest) to 5 (critical deadline/action required)", ge=1, le=5
    )
    action_required: bool = Field(description="Whether explicit action/reply is required")
    suggested_action: str = Field(description="Concise description of the next best action")
    sentiment: str = Field(description="Detected tone: Positive, Neutral, Urgent/Alert, Negative")
    summary: str = Field(description="A concise one-sentence executive summary of the email")


class EmailCategorizer:
    """
    Categorizer combining semantic rule evaluation and LLM-assisted classification.
    """

    CATEGORIES = {
        "URGENT_ACTION": "🚨 Urgent / Action Required",
        "WORK_ACADEMIC": "💼 Work / Academic",
        "PERSONAL": "💬 Personal / Direct",
        "NEWSLETTERS": "📢 Newsletters & Updates",
        "PROMOTIONS": "🛍️ Promotions & Deals",
        "SPAM_PHISHING": "🗑️ Spam / Phishing",
    }

    @staticmethod
    def classify_heuristically(email: Dict[str, Any]) -> EmailClassification:
        """
        Fast heuristic classification fallback based on subject, sender, and content keywords.
        Guarantees deterministic categorization even without internet or LLM token usage.
        """
        subject = email.get("subject", "").lower()
        sender = email.get("sender", "").lower()
        body = email.get("body", "").lower()
        snippet = email.get("snippet", "").lower()
        text = f"{subject} {snippet} {body}"

        # 1. Spam & Phishing Detection
        spam_indicators = [
            "won $", "cash prize", "sweepstakes", "lottery", "beneficiary",
            "passport", "ssn", "claim pending", "nigerian", "wire transfer", "crypto payout"
        ]
        if any(term in text for term in spam_indicators):
            return EmailClassification(
                category=EmailCategorizer.CATEGORIES["SPAM_PHISHING"],
                urgency_score=1,
                action_required=False,
                suggested_action="Delete email or report as phishing. Do NOT click links.",
                sentiment="Negative",
                summary="Suspicious lottery or prize payout scam seeking personal credentials.",
            )

        # 2. Critical & Urgent / Billing / Deadlines
        urgent_indicators = [
            "urgent", "critical alert", "deadline", "exceeded", "action required",
            "immediate", "asap", "closing tomorrow", "portal will strictly close"
        ]
        if any(term in text for term in urgent_indicators) or "billing alert" in text:
            is_billing = "billing" in text or "aws" in text or "charge" in text
            return EmailClassification(
                category=EmailCategorizer.CATEGORIES["URGENT_ACTION"],
                urgency_score=5,
                action_required=True,
                suggested_action="Review immediately and draft response/take corrective action." if not is_billing else "Inspect cloud console to terminate high-cost resources.",
                sentiment="Urgent/Alert",
                summary=email.get("snippet", subject)[:140],
            )

        # 3. Work & Academic / Interview Invitations
        work_indicators = [
            "sitnagpur", "edu.in", "symbiosis", "professor", "intern", "interview",
            "project", "submission", "recruiting", "capstone", "bachelor", "candidate", "assignment"
        ]
        if any(term in text for term in work_indicators) or any(term in sender for term in [".edu", "google.com", "microsoft.com"]):
            is_interview = "interview" in text or "invitation" in text
            return EmailClassification(
                category=EmailCategorizer.CATEGORIES["WORK_ACADEMIC"],
                urgency_score=4 if is_interview else 3,
                action_required=True if is_interview or "deadline" in text or "reply" in text else False,
                suggested_action="Draft interview availability reply" if is_interview else "Acknowledge receipt and follow up on milestones.",
                sentiment="Positive" if is_interview else "Neutral",
                summary=email.get("snippet", subject)[:140],
            )

        # 4. Promotions & Commercial Marketing
        promo_indicators = [
            "sale", "50% off", "discount", "flipkart", "amazon", "deal", "limited time",
            "coupon", "order now", "mega tech"
        ]
        if any(term in text for term in promo_indicators) or "PROMOTIONS" in email.get("labels", []):
            return EmailClassification(
                category=EmailCategorizer.CATEGORIES["PROMOTIONS"],
                urgency_score=1,
                action_required=False,
                suggested_action="Archive or ignore; no action required.",
                sentiment="Positive",
                summary="Promotional offer or sales campaign.",
            )

        # 5. Newsletters & Subscriptions
        newsletter_indicators = [
            "newsletter", "weekly", "digest", "roundup", "edition", "unsubscribe", "updates from"
        ]
        if any(term in text for term in newsletter_indicators) or "NEWSLETTER" in email.get("labels", []):
            return EmailClassification(
                category=EmailCategorizer.CATEGORIES["NEWSLETTERS"],
                urgency_score=2,
                action_required=False,
                suggested_action="Read when free; archive after review.",
                sentiment="Neutral",
                summary="Informational newsletter or industry publication.",
            )

        # Default: Personal / Direct Communication
        return EmailClassification(
            category=EmailCategorizer.CATEGORIES["PERSONAL"],
            urgency_score=3,
            action_required=True,
            suggested_action="Review and reply to sender.",
            sentiment="Neutral",
            summary=email.get("snippet", subject)[:140],
        )

    @classmethod
    def categorize_inbox(cls, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Categorize a collection of emails and return enriched metadata."""
        categorized_list = []
        for em in emails:
            classification = cls.classify_heuristically(em)
            enriched = dict(em)
            enriched["classification"] = classification.model_dump()
            categorized_list.append(enriched)
        return categorized_list
