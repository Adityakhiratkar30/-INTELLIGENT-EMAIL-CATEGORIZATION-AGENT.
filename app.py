"""
==============================================================================
Intelligent Email Categorization Agent - Interactive Web Dashboard
Student Name : Aditya khiratkar
PRN          : 24070521071
Institute    : Symbiosis Institute of Technology, Nagpur
==============================================================================
Launches a responsive visual dashboard demonstrating real-time email triage,
multi-class categorization, AI draft generation, and Human-in-the-Loop gating.
Uses Python's standard library http.server for 100% zero-friction execution.
"""

import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from gmail_service import get_active_gmail_service, MockGmailService
from email_categorizer import EmailCategorizer
from agent import create_email_agent, SENSITIVE_TOOL_POLICY
from langgraph.types import Command

PORT = 5000
agent_instance, active_service = create_email_agent()
pending_interrupts = {}
session_config = {"configurable": {"thread_id": "web_dashboard_session_1"}}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Intelligent Email Categorization Agent | Aditya khiratkar</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #131b2e;
            --bg-card: rgba(26, 36, 61, 0.7);
            --border: rgba(255, 255, 255, 0.08);
            --accent: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.3);
            --urgent: #ef4444;
            --work: #3b82f6;
            --personal: #10b981;
            --newsletter: #8b5cf6;
            --promo: #f59e0b;
            --spam: #6b7280;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(59, 130, 246, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(139, 92, 246, 0.12) 0%, transparent 40%);
        }

        /* Top Header */
        header {
            background: rgba(19, 27, 46, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-icon {
            width: 42px;
            height: 42px;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 14px var(--accent-glow);
        }

        .brand-info h1 {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .brand-info p {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .student-pill {
            background: rgba(59, 130, 246, 0.12);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 100px;
            padding: 6px 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.82rem;
        }

        .student-name {
            font-weight: 600;
            color: #60a5fa;
        }

        .student-prn {
            font-family: 'JetBrains Mono', monospace;
            background: rgba(255, 255, 255, 0.08);
            padding: 2px 8px;
            border-radius: 6px;
            color: var(--text-main);
        }

        /* Main Container */
        .container {
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 2rem;
            display: grid;
            grid-template-columns: 320px 1fr 380px;
            gap: 1.5rem;
            flex: 1;
        }

        /* Sidebar Stats & Controls */
        .sidebar, .chat-panel {
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            height: calc(100vh - 120px);
            position: sticky;
            top: 90px;
        }

        .section-title {
            font-size: 0.95rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px;
            text-align: center;
        }

        .stat-number {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--accent);
        }

        .stat-label {
            font-size: 0.72rem;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .category-filter-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            overflow-y: auto;
        }

        .filter-btn {
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-main);
            padding: 8px 12px;
            border-radius: 8px;
            text-align: left;
            font-size: 0.82rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
        }

        .filter-btn:hover, .filter-btn.active {
            background: rgba(255, 255, 255, 0.06);
            border-color: var(--border);
        }

        .count-badge {
            background: rgba(255, 255, 255, 0.1);
            padding: 2px 7px;
            border-radius: 10px;
            font-size: 0.7rem;
            font-weight: 600;
        }

        .hitl-badge-box {
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.25);
            border-radius: 10px;
            padding: 12px;
            font-size: 0.78rem;
            line-height: 1.4;
        }

        .hitl-badge-box strong {
            color: #f87171;
            display: block;
            margin-bottom: 4px;
        }

        /* Central Inbox Area */
        .inbox-area {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .inbox-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1rem 1.5rem;
        }

        .inbox-header h2 {
            font-size: 1.25rem;
            font-weight: 700;
        }

        .action-btns {
            display: flex;
            gap: 10px;
        }

        .btn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }

        .btn:hover {
            background: #2563eb;
            box-shadow: 0 4px 12px var(--accent-glow);
        }

        .btn-outline {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--text-main);
        }

        .btn-outline:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .email-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .email-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.25rem;
            transition: all 0.2s;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }

        .email-card:hover {
            border-color: rgba(59, 130, 246, 0.4);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }

        .email-card.urgent {
            border-left: 4px solid var(--urgent);
        }

        .email-card.work {
            border-left: 4px solid var(--work);
        }

        .email-card.newsletter {
            border-left: 4px solid var(--newsletter);
        }

        .email-card.promo {
            border-left: 4px solid var(--promo);
        }

        .email-card.spam {
            border-left: 4px solid var(--spam);
        }

        .card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }

        .sender-info {
            font-size: 0.85rem;
            font-weight: 600;
            color: #93c5fd;
        }

        .badge {
            font-size: 0.72rem;
            padding: 3px 10px;
            border-radius: 100px;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .badge-urgent { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge-work { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
        .badge-newsletter { background: rgba(139, 92, 246, 0.15); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }
        .badge-promo { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-spam { background: rgba(107, 114, 128, 0.15); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.3); }

        .email-subject {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 6px;
        }

        .email-snippet {
            font-size: 0.84rem;
            color: var(--text-muted);
            line-height: 1.5;
            margin-bottom: 10px;
        }

        .card-bottom {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: var(--text-muted);
            border-top: 1px solid rgba(255, 255, 255, 0.04);
            padding-top: 8px;
        }

        .urgency-dots {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.15);
        }

        .dot.active {
            background: #ef4444;
        }

        /* Right Agent Chat Panel */
        .chat-panel {
            display: flex;
            flex-direction: column;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding-right: 4px;
        }

        .msg {
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 0.84rem;
            line-height: 1.5;
            max-width: 90%;
        }

        .msg-user {
            align-self: flex-end;
            background: #2563eb;
            color: white;
            border-bottom-right-radius: 2px;
        }

        .msg-agent {
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border);
            color: var(--text-main);
            border-bottom-left-radius: 2px;
        }

        .chat-input-box {
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }

        .chat-input {
            flex: 1;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 14px;
            color: white;
            font-size: 0.85rem;
            outline: none;
        }

        .chat-input:focus {
            border-color: var(--accent);
        }

        /* Modal for Human-In-The-Loop Approval */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }

        .modal-content {
            background: #111827;
            border: 1px solid rgba(239, 68, 68, 0.4);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
            border-radius: 16px;
            max-width: 600px;
            width: 90%;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            animation: modalPop 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes modalPop {
            from { transform: scale(0.92); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }

        .modal-header {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .modal-icon {
            width: 44px;
            height: 44px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }

        .modal-body {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1rem;
            font-size: 0.85rem;
            display: flex;
            flex-direction: column;
            gap: 8px;
            font-family: 'JetBrains Mono', monospace;
        }

        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 8px;
        }

        .btn-approve { background: #10b981; }
        .btn-approve:hover { background: #059669; }
        .btn-reject { background: #ef4444; }
        .btn-reject:hover { background: #dc2626; }
        .btn-edit { background: #f59e0b; }
        .btn-edit:hover { background: #d97706; }
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <div class="brand-icon">📬</div>
            <div class="brand-info">
                <h1>Intelligent Email Categorization Agent</h1>
                <p>LangChain & LangGraph Multi-Agent Architecture • Gmail API</p>
            </div>
        </div>
        <div class="student-pill">
            <span>Student:</span>
            <span class="student-name">Aditya khiratkar</span>
            <span>PRN:</span>
            <span class="student-prn">24070521071</span>
        </div>
    </header>

    <div class="container">
        <!-- Left Sidebar -->
        <aside class="sidebar">
            <div class="section-title">📊 Inbox Intelligence</div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="stat-total">6</div>
                    <div class="stat-label">Total Analyzed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="stat-urgent" style="color: var(--urgent)">2</div>
                    <div class="stat-label">Urgent / Action</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="stat-work" style="color: var(--work)">1</div>
                    <div class="stat-label">Academic / Work</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="stat-spam" style="color: var(--spam)">1</div>
                    <div class="stat-label">Spam / Phishing</div>
                </div>
            </div>

            <div class="section-title">🏷️ Categories Filter</div>
            <div class="category-filter-list">
                <button class="filter-btn active" onclick="filterEmails('ALL')">All Messages <span class="count-badge" id="badge-all">6</span></button>
                <button class="filter-btn" onclick="filterEmails('Urgent')">🚨 Urgent / Action <span class="count-badge" id="badge-urgent">2</span></button>
                <button class="filter-btn" onclick="filterEmails('Work')">💼 Work / Academic <span class="count-badge" id="badge-work">1</span></button>
                <button class="filter-btn" onclick="filterEmails('Newsletters')">📢 Newsletters <span class="count-badge" id="badge-newsletter">1</span></button>
                <button class="filter-btn" onclick="filterEmails('Promotions')">🛍️ Promotions <span class="count-badge" id="badge-promo">1</span></button>
                <button class="filter-btn" onclick="filterEmails('Spam')">🗑️ Spam / Phishing <span class="count-badge" id="badge-spam">1</span></button>
            </div>

            <div class="hitl-badge-box">
                <strong>🛡️ HITL Safety Gating</strong>
                Sensitive tool calls (Send, Draft, Delete) are locked behind explicit user authorization. Autonomous triage runs safely in sandbox mode.
            </div>
        </aside>

        <!-- Center Email Feed -->
        <main class="inbox-area">
            <div class="inbox-header">
                <div>
                    <h2>Triaged Inbox Messages</h2>
                    <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">Ranked by Priority & Urgency Score</p>
                </div>
                <div class="action-btns">
                    <button class="btn btn-outline" onclick="loadEmails()">🔄 Refresh</button>
                    <button class="btn" onclick="triggerTriageRun()">⚡ Run AI Triage</button>
                </div>
            </div>

            <div class="email-list" id="email-list-container">
                <!-- Injected via JavaScript -->
            </div>
        </main>

        <!-- Right Agent Chat & Co-Pilot -->
        <aside class="chat-panel">
            <div class="section-title">🤖 Agent Co-Pilot (HITL)</div>
            <div class="chat-messages" id="chat-messages">
                <div class="msg msg-agent">
                    Hello Aditya! I am your <strong>Intelligent Email Categorization Agent</strong>. I have triaged your inbox. What would you like me to execute?
                </div>
            </div>
            <div class="chat-input-box">
                <input type="text" id="chat-input" class="chat-input" placeholder="Type prompt (e.g. Reply to Dr. Sharma)..." onkeydown="handleChatKey(event)">
                <button class="btn" onclick="sendChatPrompt()">Send</button>
            </div>
        </aside>
    </div>

    <!-- Human-In-The-Loop Approval Modal -->
    <div class="modal-overlay" id="hitl-modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-icon">🛑</div>
                <div>
                    <h3 style="color: #f87171;">Human-In-The-Loop Action Required</h3>
                    <p style="font-size: 0.8rem; color: var(--text-muted);">Gated Tool Call Intercepted for Safety Verification</p>
                </div>
            </div>
            <div class="modal-body" id="modal-details">
                <!-- Injected action details -->
            </div>
            <div class="modal-actions">
                <button class="btn btn-reject" onclick="resolveDecision('reject')">❌ Reject</button>
                <button class="btn btn-edit" onclick="resolveDecision('edit')">✏️ Edit Args</button>
                <button class="btn btn-approve" onclick="resolveDecision('approve')">✅ Approve & Send</button>
            </div>
        </div>
    </div>

    <script>
        let allEmails = [];
        let activeFilter = 'ALL';
        let pendingInterruptData = null;

        async function loadEmails() {
            try {
                const res = await fetch('/api/inbox');
                const data = await res.json();
                allEmails = data.emails || [];
                renderEmails();
            } catch (e) {
                console.error("Error loading emails:", e);
            }
        }

        function renderEmails() {
            const container = document.getElementById('email-list-container');
            container.innerHTML = '';

            const filtered = allEmails.filter(e => {
                if (activeFilter === 'ALL') return true;
                const cat = e.classification?.category || '';
                return cat.toLowerCase().includes(activeFilter.toLowerCase());
            });

            if (filtered.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding: 2rem; color: var(--text-muted);">No emails in this category.</div>';
                return;
            }

            filtered.forEach(e => {
                const cls = e.classification || {};
                let catClass = 'work';
                let badgeClass = 'badge-work';
                const catText = cls.category || 'Standard';

                if (catText.includes('Urgent')) { catClass = 'urgent'; badgeClass = 'badge-urgent'; }
                else if (catText.includes('Newsletter')) { catClass = 'newsletter'; badgeClass = 'badge-newsletter'; }
                else if (catText.includes('Promotion')) { catClass = 'promo'; badgeClass = 'badge-promo'; }
                else if (catText.includes('Spam')) { catClass = 'spam'; badgeClass = 'badge-spam'; }

                const card = document.createElement('div');
                card.className = `email-card ${catClass}`;
                card.innerHTML = `
                    <div class="card-top">
                        <span class="sender-info">${e.sender}</span>
                        <span class="badge ${badgeClass}">${cls.category}</span>
                    </div>
                    <div class="email-subject">${e.subject}</div>
                    <div class="email-snippet">${e.body || e.snippet}</div>
                    <div class="card-bottom">
                        <div class="urgency-dots">
                            <span style="font-weight: 600; margin-right: 4px;">Priority: ${cls.urgency_score || 3}/5</span>
                            ${[1,2,3,4,5].map(i => `<span class="dot ${(i <= (cls.urgency_score||1)) ? 'active':''}"></span>`).join('')}
                        </div>
                        <button class="btn btn-outline" style="padding: 4px 10px; font-size: 0.75rem;" onclick="event.stopPropagation(); prepareDraft('${e.id}', '${escapeHtml(e.sender)}')">✉️ Draft Response</button>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        function escapeHtml(text) {
            return (text || '').replace(/'/g, "\\\\'");
        }

        function filterEmails(category) {
            activeFilter = category;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            renderEmails();
        }

        function appendMessage(role, text) {
            const container = document.getElementById('chat-messages');
            const msg = document.createElement('div');
            msg.className = `msg msg-${role}`;
            msg.innerHTML = text.replace(/\\n/g, '<br>');
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
        }

        async function sendChatPrompt() {
            const input = document.getElementById('chat-input');
            const prompt = input.value.trim();
            if (!prompt) return;

            appendMessage('user', prompt);
            input.value = '';

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt})
                });
                const data = await res.json();

                if (data.interrupt) {
                    showHitlModal(data.interrupt);
                } else if (data.response) {
                    appendMessage('agent', data.response);
                }
            } catch (e) {
                appendMessage('agent', 'Error contacting agent co-pilot: ' + e);
            }
        }

        function handleChatKey(e) {
            if (e.key === 'Enter') sendChatPrompt();
        }

        function prepareDraft(id, sender) {
            document.getElementById('chat-input').value = `Reply to ${sender} regarding email ${id} with professional acknowledgment`;
            sendChatPrompt();
        }

        function triggerTriageRun() {
            document.getElementById('chat-input').value = "Perform complete inbox categorization report";
            sendChatPrompt();
        }

        function showHitlModal(interruptData) {
            pendingInterruptData = interruptData;
            const req = interruptData.requests?.[0]?.action_request || {};
            const details = document.getElementById('modal-details');
            details.innerHTML = `
                <div><strong>Action:</strong> <span style="color: #60a5fa">${req.name || req.action}</span></div>
                <div><strong>To:</strong> ${req.args?.to || 'N/A'}</div>
                <div><strong>Subject:</strong> ${req.args?.subject || 'N/A'}</div>
                <div style="margin-top: 6px;"><strong>Body Preview:</strong><br><span style="color: #cbd5e1">${req.args?.message || JSON.stringify(req.args)}</span></div>
            `;
            document.getElementById('hitl-modal').style.display = 'flex';
        }

        async function resolveDecision(decisionType) {
            document.getElementById('hitl-modal').style.display = 'none';

            let decisionPayload = { type: decisionType };
            if (decisionType === 'reject') {
                decisionPayload.message = "User manually rejected via Web Dashboard.";
            } else if (decisionType === 'edit') {
                const newSubject = prompt("Enter modified Subject line:", pendingInterruptData?.requests?.[0]?.action_request?.args?.subject || "");
                const req = pendingInterruptData?.requests?.[0]?.action_request || {};
                const args = Object.assign({}, req.args, { subject: newSubject });
                decisionPayload = {
                    type: "edit",
                    edited_action: { name: req.name || req.action, args: args }
                };
            }

            try {
                const res = await fetch('/api/decision', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ decisions: [decisionPayload] })
                });
                const data = await res.json();
                appendMessage('agent', data.response || "Action resolved and recorded.");
                loadEmails();
            } catch (e) {
                appendMessage('agent', "Error resolving action: " + e);
            }
        }

        // Initial Load
        loadEmails();
    </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif parsed.path == "/api/inbox":
            # Return categorized emails
            if isinstance(active_service, MockGmailService):
                emails = active_service.search_emails()
            else:
                emails = []

            categorized = EmailCategorizer.categorize_inbox(emails)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"emails": categorized}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8")
        data = json.loads(post_body) if post_body else {}

        if parsed.path == "/api/chat":
            prompt = data.get("prompt", "")
            payload = {"messages": [{"role": "user", "content": prompt}]}
            result = agent_instance.invoke(payload, config=session_config)

            if result.get("__interrupt__"):
                interrupt_obj = result["__interrupt__"][0]
                val = interrupt_obj.value
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

                pending_interrupts["current"] = requests_to_process

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "interrupt": {
                        "requests": requests_to_process
                    }
                }).encode("utf-8"))
            else:
                last_msg = result["messages"][-1].content
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"response": last_msg}).encode("utf-8"))

        elif parsed.path == "/api/decision":
            decisions = data.get("decisions", [{"type": "approve"}])
            resumed = agent_instance.invoke(Command(resume={"decisions": decisions}), config=session_config)
            last_msg = resumed["messages"][-1].content
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"response": last_msg}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress routine HTTP request logging for cleaner terminal output
        return


def run_server(port: int = PORT):
    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    print("=" * 80)
    print("  INTELLIGENT EMAIL CATEGORIZATION AGENT - WEB DASHBOARD")
    print(f"  Student : Aditya khiratkar (PRN: 24070521071)")
    print(f"  Live UI : http://localhost:{port}")
    print("=" * 80)
    print(f"Server running on port {port}. Press Ctrl+C to terminate.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb dashboard stopped.")
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else PORT
    run_server(port)
