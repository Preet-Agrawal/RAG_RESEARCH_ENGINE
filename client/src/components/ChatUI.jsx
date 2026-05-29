import { useState, useRef, useEffect } from 'react';
import StrategySelector from './StrategySelector.jsx';

function formatStrategy(name) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function MessageMeta({ metadata }) {
  if (!metadata) return null;
  const confidence = metadata.confidence;
  const confidenceClass =
    confidence >= 0.75
      ? 'badge-success'
      : confidence >= 0.5
        ? 'badge-warn'
        : 'badge-danger';

  return (
    <div className="message-meta">
      {confidence != null && (
        <span className={`badge ${confidenceClass}`}>
          {Math.round(confidence * 100)}% confidence
        </span>
      )}
      {metadata.latency != null && (
        <span className="meta-chip">{metadata.latency.toFixed(2)}s</span>
      )}
      {metadata.chunksProcessed != null && (
        <span className="meta-chip">{metadata.chunksProcessed} chunks</span>
      )}
      {metadata.strategyUsed && (
        <span className="meta-chip accent">
          {formatStrategy(metadata.strategyUsed)}
        </span>
      )}
      {metadata.strategyExplanation && (
        <p className="strategy-explanation">{metadata.strategyExplanation}</p>
      )}
    </div>
  );
}

function SummaryBlock({ summaryData }) {
  if (!summaryData) return null;
  return (
    <div className="summary-block">
      <h3 className="summary-title">Document overview</h3>
      <p className="summary-overall">{summaryData.overallSummary}</p>
      <div className="chunk-list">
        {summaryData.chunkSummaries.map((chunk) => (
          <div
            key={chunk.chunkId}
            className={`chunk-item ${chunk.isMiddle ? 'chunk-middle' : ''}`}
          >
            <span className="chunk-label">
              Section {chunk.chunkId}/{chunk.totalChunks}
              <span className={`zone-tag ${chunk.zone === 'middle' ? 'zone-middle' : ''}`}>
                {chunk.zone}
              </span>
            </span>
            <p>{chunk.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ChatUI({
  messages,
  onSendMessage,
  isLoading,
  isProcessing,
  processingLabel,
  disabled,
  selectedStrategy,
  onStrategyChange,
  summaryData,
  documentName,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || disabled || isLoading) return;
    setInput('');
    await onSendMessage(text);
  };

  const suggested = [
    'What are the main findings?',
    'Summarize the methodology',
    'What data is in the middle sections?',
  ];

  return (
    <div className="chat-ui">
      <div className="chat-messages">
        {messages.length === 0 && !isProcessing && (
          <p className="chat-placeholder">
            Ask a question about {documentName || 'your document'}.
          </p>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`message message-${msg.role}`}>
            <div className="message-bubble">
              {msg.content === '__SUMMARY__' ? (
                <SummaryBlock summaryData={summaryData} />
              ) : (
                <div className="message-text">{msg.content}</div>
              )}
              {msg.role === 'assistant' && msg.content !== '__SUMMARY__' && (
                <MessageMeta metadata={msg.metadata} />
              )}
            </div>
          </div>
        ))}

        {isProcessing && (
          <div className="message message-assistant">
            <div className="message-bubble">
              <div className="typing-indicator">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
              <p className="processing-label">{processingLabel}</p>
            </div>
          </div>
        )}

        {isLoading && !isProcessing && (
          <div className="message message-assistant">
            <div className="message-bubble">
              <div className="typing-indicator">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {messages.length <= 1 && !disabled && (
        <div className="suggested-questions">
          {suggested.map((q) => (
            <button
              key={q}
              type="button"
              className="suggested-btn"
              onClick={() => onSendMessage(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <div className="chat-footer">
        <StrategySelector
          value={selectedStrategy}
          onChange={onStrategyChange}
          disabled={disabled || isLoading}
        />
        <form className="chat-input-form" onSubmit={handleSubmit}>
          <textarea
            className="chat-input"
            rows={1}
            placeholder="Ask a question about the document..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            disabled={disabled || isLoading}
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={disabled || isLoading || !input.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
