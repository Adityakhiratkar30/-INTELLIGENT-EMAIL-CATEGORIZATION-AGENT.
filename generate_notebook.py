"""
==============================================================================
Intelligent Email Categorization Agent - Notebook Builder
Student Name : Aditya khiratkar
PRN          : 24070521071
==============================================================================
Generates the clean, fully functional main.ipynb with all imports,
HITL middleware, Gmail integration, and test queries.
"""

import json

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Intelligent Email Categorization Agent\n",
            "\n",
            "**STUDENT CREDENTIALS:**\n",
            "- **Name:** Aditya khiratkar\n",
            "- **PRN:** 24070521071\n",
            "- **Institute:** Symbiosis Institute of Technology, Nagpur\n",
            "- **Course:** Agentic AI & Automation\n",
            "\n",
            "---\n",
            "\n",
            "## 📌 Project Overview\n",
            "The **Intelligent Email Categorization Agent** is an agentic AI system designed using **LangChain**, **LangGraph**, and the **Gmail API**.\n",
            "It autonomously triages incoming emails, performs multi-class categorization into structured buckets, and drafts contextual responses via LLM tool-calling.\n",
            "\n",
            "### 🛡️ Human-in-the-Loop (HITL) Safety Policy\n",
            "- **Autonomous Operations:** Read-only actions (`search_gmail`, `get_gmail_message`, `get_gmail_thread`, `categorize_emails`) execute without interruption.\n",
            "- **Gated Actions:** High-consequence or irreversible operations (`send_gmail_message`, `create_gmail_draft`, `delete_gmail_message`) are intercepted before execution.\n",
            "- **Review Decisions:** The human operator can **approve**, **edit** parameters (recipient, subject, body), or **reject** with feedback before anything is committed."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 1: Import core dependencies\n",
            "import os\n",
            "from dotenv import load_dotenv\n",
            "from langchain_community.agent_toolkits import GmailToolkit\n",
            "from langchain_community.tools.gmail.utils import (\n",
            "    build_resource_service,\n",
            "    get_gmail_credentials,\n",
            ")\n",
            "from langchain.agents import create_agent\n",
            "from langchain.agents.middleware import HumanInTheLoopMiddleware\n",
            "from langchain_openai import ChatOpenAI\n",
            "from langgraph.checkpoint.memory import InMemorySaver\n",
            "from langgraph.types import Command\n",
            "\n",
            "# Import local service and categorization modules\n",
            "from gmail_service import get_active_gmail_service, MockGmailService\n",
            "from email_categorizer import EmailCategorizer\n",
            "from agent import (\n",
            "    build_tools,\n",
            "    SENSITIVE_TOOL_POLICY,\n",
            "    describe_action_request,\n",
            "    ask_human_for_decision,\n",
            "    run_with_approval,\n",
            "    get_llm,\n",
            ")\n",
            "\n",
            "print(\"✅ All modules and dependencies imported successfully.\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 2: Load environment variables and check API credentials\n",
            "load_dotenv()\n",
            "\n",
            "api_key = os.getenv(\"OPENAI_API_KEY\")\n",
            "if api_key and not api_key.startswith(\"your_openai\"):\n",
            "    print(f\"🔑 OpenAI API Key configured: {api_key[:6]}...{api_key[-4:]}\")\n",
            "else:\n",
            "    print(\"ℹ️ No live OPENAI_API_KEY detected in .env.\")\n",
            "    print(\"   Agent will utilize internal demonstration LLM for safe offline testing.\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 3: Initialize Gmail Service and build agent tools\n",
            "# Automatically activates live Google Cloud Gmail API if credentials.json is present,\n",
            "# otherwise loads the interactive Mock Mailbox sandbox with sample academic and professional emails.\n",
            "gmail_service = get_active_gmail_service()\n",
            "tools = build_tools(gmail_service)\n",
            "\n",
            "print(f\"Loaded {len(tools)} tools for email triage:\")\n",
            "for t in tools:\n",
            "    print(f\"  • {t.name:<22}: {t.description[:65]}...\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 4: Configure Human-in-the-Loop (HITL) Middleware\n",
            "hitl_middleware = HumanInTheLoopMiddleware(\n",
            "    interrupt_on=SENSITIVE_TOOL_POLICY,\n",
            "    description_prefix=\"Tool execution pending human approval\",\n",
            ")\n",
            "\n",
            "print(\"Safety Policy Matrix:\")\n",
            "for tool_name, policy in SENSITIVE_TOOL_POLICY.items():\n",
            "    if isinstance(policy, dict):\n",
            "        print(f\"  🔒 GATED      : {tool_name:<22} -> Allowed: {policy['allowed_decisions']}\")\n",
            "    else:\n",
            "        print(f\"  ⚡ AUTONOMOUS : {tool_name:<22} -> Direct execution\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 5: System Instructions & LLM Initialization\n",
            "instructions = (\n",
            "    \"You are the Intelligent Email Categorization Agent created by Aditya khiratkar (PRN: 24070521071).\\n\"\n",
            "    \"Your mission is to triage emails, categorize them into Urgent/Action Required, Work/Academic, \\n\"\n",
            "    \"Personal, Newsletters, Promotions, and Spam, and draft polite, concise responses.\\n\\n\"\n",
            "    \"Sending or drafting messages will always pause for human approval, so feel free to prepare a send \\n\"\n",
            "    \"or draft action when appropriate. A human reviews and confirms it before anything leaves the inbox.\"\n",
            ")\n",
            "\n",
            "llm = get_llm()\n",
            "print(\"LLM engine initialized:\", type(llm).__name__)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 6: Create Agent with Checkpointer & Middleware\n",
            "checkpointer = InMemorySaver()\n",
            "\n",
            "agent = create_agent(\n",
            "    model=llm,\n",
            "    tools=tools,\n",
            "    system_prompt=instructions,\n",
            "    middleware=[hitl_middleware],\n",
            "    checkpointer=checkpointer,\n",
            ")\n",
            "print(\"✅ Intelligent Email Categorization Agent compiled successfully!\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 7: Configure conversation thread\n",
            "config = {\"configurable\": {\"thread_id\": \"aditya_email_session_101\"}}\n",
            "print(\"Active thread session config:\", config)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 8: Test Query 1 - Autonomous Read-Only Triage\n",
            "# Request that should NOT trigger an interrupt\n",
            "input_command = {\n",
            "    \"messages\": [\n",
            "        {\"role\": \"user\", \"content\": \"Categorize my recent emails and summarize urgent items.\"}\n",
            "    ]\n",
            "}\n",
            "\n",
            "print(\"Submitting read-only prompt to agent...\")\n",
            "result = run_with_approval(agent, input_command, config)\n",
            "print(\"\\n--- Agent Response ---\")\n",
            "print(result[\"messages\"][-1].content)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 9: Test Query 2 - High-Stakes Action Requiring Human Approval\n",
            "# Request that SHOULD trigger an interrupt (drafting or sending email)\n",
            "input_command = {\n",
            "    \"messages\": [\n",
            "        {\"role\": \"user\", \"content\": \"Reply to Dr. Sharma confirming that my Capstone project report and repository will be submitted before 5 PM tomorrow.\"}\n",
            "    ]\n",
            "}\n",
            "\n",
            "print(\"Submitting sensitive prompt to agent...\")\n",
            "result = run_with_approval(agent, input_command, config)\n",
            "print(\"\\n--- Agent Response ---\")\n",
            "print(result[\"messages\"][-1].content)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 10: Multi-Class Email Categorization Pipeline Table\n",
            "# Detailed breakdown of inbox messages across urgency scores, categories, and actions\n",
            "sample_inbox = gmail_service.search_emails() if hasattr(gmail_service, \"search_emails\") else []\n",
            "if sample_inbox:\n",
            "    categorized = EmailCategorizer.categorize_inbox(sample_inbox)\n",
            "    print(f\"{'ID':<8} | {'CATEGORY':<30} | {'PRIORITY':<8} | {'SUBJECT':<45}\")\n",
            "    print(\"-\" * 98)\n",
            "    for item in categorized:\n",
            "        cls_info = item['classification']\n",
            "        print(f\"{item['id']:<8} | {cls_info['category']:<30} | {cls_info['urgency_score']}/5     | {item['subject'][:43]:<45}\")\n",
            "else:\n",
            "    print(\"Live Gmail connected. Use search_gmail or categorize_emails tools to inspect messages.\")"
        ]
    }
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.14.5"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

with open("d:/Intelligent_Email_Categorization_Agent/main.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)

print("[OK] main.ipynb written successfully!")
