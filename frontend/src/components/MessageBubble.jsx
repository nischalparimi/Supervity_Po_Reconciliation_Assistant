import SqlExpander from './SqlExpander';

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function UserMessage({ msg }) {
  return (
    <div className="message user">
      <div className="message-meta">
        <span className="message-time">{formatTime(msg.timestamp)}</span>
        <span className="message-role">You</span>
      </div>
      <div className="message-bubble">{msg.text}</div>
    </div>
  );
}

function AssistantMessage({ msg }) {
  // Render markdown-like line breaks
  const lines = msg.text.split('\n');

  return (
    <div className="message assistant">
      <div className="message-meta">
        <span className="message-role">Assistant</span>
        <span className="message-time">{formatTime(msg.timestamp)}</span>
      </div>
      <div className="message-bubble">
        {lines.map((line, i) => (
          <span key={i}>
            {line}
            {i < lines.length - 1 && <br />}
          </span>
        ))}
      </div>
      {msg.sql !== undefined && (
        <SqlExpander
          sql={msg.sql}
          rows={msg.rows}
          columns={msg.columns}
          rowCount={msg.rowCount}
        />
      )}
    </div>
  );
}

export default function MessageBubble({ msg }) {
  if (msg.role === 'user') return <UserMessage msg={msg} />;
  return <AssistantMessage msg={msg} />;
}
