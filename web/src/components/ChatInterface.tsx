'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Zap, Clock, Layers, Info } from 'lucide-react';
import type { Message, Strategy } from '@/types';
import { STRATEGIES } from '@/types';

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (message: string) => Promise<void>;
  isLoading?: boolean;
  disabled?: boolean;
  selectedStrategy: Strategy;
  onStrategyChange: (strategy: Strategy) => void;
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const percentage = Math.round(confidence * 100);
  let colorClass = 'bg-green-500/20 text-green-400 border-green-500/30';

  if (confidence < 0.5) {
    colorClass = 'bg-red-500/20 text-red-400 border-red-500/30';
  } else if (confidence < 0.75) {
    colorClass = 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${colorClass}`}>
      <Zap className="w-3 h-3" />
      {percentage}% confidence
    </span>
  );
}

function MetadataDisplay({ metadata }: { metadata: Message['metadata'] }) {
  if (!metadata) return null;

  return (
    <div className="mt-3 pt-3 border-t border-claude-border/50 space-y-2">
      <div className="flex flex-wrap gap-2 text-xs">
        {metadata.confidence !== undefined && (
          <ConfidenceBadge confidence={metadata.confidence} />
        )}
        {metadata.latency !== undefined && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
            <Clock className="w-3 h-3" />
            {metadata.latency.toFixed(2)}s
          </span>
        )}
        {metadata.chunksProcessed !== undefined && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
            <Layers className="w-3 h-3" />
            {metadata.chunksProcessed} chunks
          </span>
        )}
      </div>
      {metadata.strategyUsed && (
        <div className="text-xs text-claude-text-secondary">
          <span className="font-medium">Strategy:</span> {metadata.strategyUsed}
        </div>
      )}
      {metadata.strategyExplanation && (
        <div className="text-xs text-claude-text-secondary flex items-start gap-1">
          <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
          {metadata.strategyExplanation}
        </div>
      )}
    </div>
  );
}

export default function ChatInterface({
  messages,
  onSendMessage,
  isLoading = false,
  disabled = false,
  selectedStrategy,
  onStrategyChange,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const [showStrategyInfo, setShowStrategyInfo] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;

    const message = input.trim();
    setInput('');
    await onSendMessage(message);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const currentStrategy = STRATEGIES.find(s => s.id === selectedStrategy);

  return (
    <div className="flex flex-col h-full">
      {/* Strategy Selector */}
      <div className="border-b border-claude-border px-4 py-3 bg-claude-surface/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-claude-text">
              Recovery Strategy:
            </label>
            <select
              value={selectedStrategy}
              onChange={(e) => onStrategyChange(e.target.value as Strategy)}
              disabled={isLoading}
              className="px-3 py-1.5 bg-claude-surface border border-claude-border rounded-lg text-sm text-claude-text focus:outline-none focus:ring-2 focus:ring-claude-accent/50 disabled:opacity-50"
            >
              {STRATEGIES.map((strategy) => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setShowStrategyInfo(!showStrategyInfo)}
              className="p-1 text-claude-text-secondary hover:text-claude-text transition-colors"
              title="Strategy info"
            >
              <Info className="w-4 h-4" />
            </button>
          </div>
        </div>
        {showStrategyInfo && currentStrategy && (
          <div className="mt-2 p-3 bg-claude-bg rounded-lg border border-claude-border text-sm">
            <p className="text-claude-text font-medium">{currentStrategy.name}</p>
            <p className="text-claude-text-secondary mt-1">{currentStrategy.description}</p>
            <div className="mt-2 pt-2 border-t border-claude-border">
              <p className="text-xs text-claude-text-secondary">
                <strong>Lost in the Middle:</strong> LLMs tend to ignore content in the middle of long documents.
                Our strategies restructure content and add attention anchors to recover this "lost" information.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <h2 className="text-2xl font-semibold text-claude-text mb-2">
                Lost in the Middle Recovery
              </h2>
              <p className="text-claude-text-secondary mb-4">
                Upload a PDF and ask questions. Our strategies help the LLM recover information
                from the middle of documents that would normally be "lost."
              </p>
              <div className="text-left bg-claude-surface border border-claude-border rounded-lg p-4 text-sm">
                <p className="font-medium text-claude-text mb-2">How it works:</p>
                <ul className="space-y-1 text-claude-text-secondary">
                  <li>1. Upload your PDF document</li>
                  <li>2. Select a recovery strategy</li>
                  <li>3. Ask questions - we'll optimize for middle content</li>
                  <li>4. Compare results with different strategies</li>
                </ul>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`
                    max-w-[85%] rounded-2xl px-4 py-3
                    ${message.role === 'user'
                      ? 'bg-claude-accent text-white'
                      : 'bg-claude-surface text-claude-text border border-claude-border'
                    }
                  `}
                >
                  <div className="whitespace-pre-wrap break-words">
                    {message.content}
                  </div>
                  {message.role === 'assistant' && message.metadata && (
                    <MetadataDisplay metadata={message.metadata} />
                  )}
                  <div
                    className={`text-xs mt-2 ${
                      message.role === 'user' ? 'text-white/70' : 'text-claude-text-secondary'
                    }`}
                  >
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-claude-surface border border-claude-border rounded-2xl px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-5 h-5 animate-spin text-claude-accent" />
                    <span className="text-sm text-claude-text-secondary">
                      Processing with {currentStrategy?.name || selectedStrategy}...
                    </span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-claude-border p-4">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="relative flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  disabled
                    ? 'Upload a PDF to start asking questions...'
                    : 'Ask a question about your document...'
                }
                disabled={disabled || isLoading}
                rows={1}
                className="
                  w-full px-4 py-3 pr-12
                  bg-claude-surface border border-claude-border
                  rounded-xl resize-none
                  text-claude-text placeholder-claude-text-secondary
                  focus:outline-none focus:ring-2 focus:ring-claude-accent/50
                  disabled:opacity-50 disabled:cursor-not-allowed
                  max-h-32 overflow-y-auto
                "
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading || disabled}
              className="
                p-3 bg-claude-accent hover:bg-claude-accent-hover
                text-white rounded-xl
                transition-colors duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
                flex-shrink-0
              "
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-xs text-claude-text-secondary mt-2 text-center">
            Press Enter to send, Shift + Enter for new line
          </p>
        </form>
      </div>
    </div>
  );
}
