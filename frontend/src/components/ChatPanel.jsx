import { useEffect, useRef, useState } from 'react';
import { sendChat } from '../api';
import MessageBubble from './MessageBubble';

const SUGGESTIONS = [
  'Which POs have unmatched receipts with invoices over $1,000?',
  'Show all quantity mismatches',
  'Are there any duplicate invoice numbers?',
  'What is the total invoice variance for Grainger?',
  'Which POs are still pending receipt?',
  'Show partially received POs with their shortfalls',
];

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}

function MessageSquareIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  );
}

let msgIdCounter = 0;
function newId() { return ++msgIdCounter; }

export default function ChatPanel({ onNewAnswer }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function submit(question) {
    const q = question.trim();
    if (!q || loading) return;
    setError(null);
    setInput('');

    const userMsg = {
      id: newId(), role: 'user', text: q, timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await sendChat(q);
      const assistantMsg = {
        id: newId(),
        role: 'assistant',
        text: data.answer,
        sql: data.sql,
        rows: data.rows,
        columns: data.columns,
        rowCount: data.row_count,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMsg]);
      if (onNewAnswer) onNewAnswer(data);
    } catch (err) {
      setError(err.message || 'Request failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  }

  // Auto-resize textarea
  function handleInput(e) {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  }

  const isEmpty = messages.length === 0 && !loading;

  return (
    <aside className="chat-panel">
      <div className="chat-panel-header">
        <span className="chat-panel-title">Query Assistant</span>
        <span className="chat-panel-hint">Ask in plain English</span>
      </div>

      <div className="chat-messages">
        {isEmpty ? (
          <div className="chat-empty">
            <div className="chat-empty-icon"><MessageSquareIcon /></div>
            <div>
              <div className="chat-empty-title">Ask about your POs</div>
              <p className="chat-empty-body">
                Query purchase orders, receipts, mismatches, and invoices using natural language.
              </p>
            </div>
            <div className="chat-suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="chat-suggestion-btn" onClick={() => submit(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map(msg => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {loading && (
              <div className="message assistant">
                <div className="message-meta">
                  <span className="message-role">Assistant</span>
                </div>
                <div className="thinking-indicator">
                  <span className="thinking-label">Querying database</span>
                  <div className="thinking-dots">
                    <span/><span/><span/>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        {error && <div className="error-banner">{error}</div>}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-form">
          <div className="chat-input-wrap">
            <textarea
              ref={textareaRef}
              className="chat-input"
              placeholder="Ask about mismatches, vendors, invoices…"
              value={input}
              onInput={handleInput}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
            />
          </div>
          <button
            className="chat-send-btn"
            onClick={() => submit(input)}
            disabled={!input.trim() || loading}
            title="Send (Enter)"
          >
            <SendIcon />
          </button>
        </div>
        <div className="chat-input-hint">Enter to send · Shift+Enter for new line</div>
      </div>
    </aside>
  );
}
