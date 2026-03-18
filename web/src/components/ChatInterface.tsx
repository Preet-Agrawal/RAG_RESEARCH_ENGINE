'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Zap, Clock, Layers, Info, ChevronDown, Beaker, User } from 'lucide-react';
import type { Message, Strategy, ChunkSummary } from '@/types';
import { STRATEGIES } from '@/types';
import DocumentOverview from './DocumentOverview';

interface SummaryData {
  chunkSummaries: ChunkSummary[];
  overallSummary: string;
  latency?: number;
}

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (message: string) => Promise<void>;
  isLoading?: boolean;
  isProcessing?: boolean;
  processingLabel?: string;
  disabled?: boolean;
  selectedStrategy: Strategy;
  onStrategyChange: (strategy: Strategy) => void;
  summaryData?: SummaryData | null;
  documentName?: string;
}

function MetadataDisplay({ metadata }: { metadata: Message['metadata'] }) {
  if (!metadata) return null;

  const confidence = metadata.confidence;
  const confidenceColor = !confidence ? '' :
    confidence >= 0.75 ? 'text-emerald-400' :
    confidence >= 0.5 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="mt-3 pt-3 border-t border-claude-border/30 flex flex-wrap items-center gap-3 text-xs text-claude-text-muted">
      {metadata.confidence !== undefined && (
        <span className={`flex items-center gap-1 ${confidenceColor}`}>
          <Zap className="w-3 h-3" />
          {Math.round(metadata.confidence * 100)}%
        </span>
      )}
      {metadata.latency !== undefined && (
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {metadata.latency.toFixed(2)}s
        </span>
      )}
      {metadata.chunksProcessed !== undefined && (
        <span className="flex items-center gap-1">
          <Layers className="w-3 h-3" />
          {metadata.chunksProcessed} chunks
        </span>
      )}
      {metadata.strategyUsed && (
        <span className="flex items-center gap-1">
          Strategy: {metadata.strategyUsed}
        </span>
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
  summaryData,
  documentName,
  isProcessing = false,
  processingLabel = '',
}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
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
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;
    const message = input.trim();
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
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
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && !isProcessing ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md px-6">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-claude-accent/20 to-amber-600/20 flex items-center justify-center mx-auto mb-4">
                <Beaker className="w-6 h-6 text-claude-accent" />
              </div>
              <h2 className="text-lg font-semibold text-claude-text mb-2">
                Ask about your document
              </h2>
              <p className="text-sm text-claude-text-muted leading-relaxed">
                Your document is loaded. Ask any question and the selected recovery strategy
                will help find answers even from the middle sections.
              </p>
            </div>
          </div>
        ) : (
          <div className="pb-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`py-5 px-4 ${
                  message.role === 'user' ? 'bg-transparent' : 'bg-claude-surface/40'
                }`}
              >
                <div className="max-w-chat mx-auto flex gap-4">
                  {/* Avatar */}
                  <div className="flex-shrink-0 mt-0.5">
                    {message.role === 'assistant' ? (
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-claude-accent to-amber-600 flex items-center justify-center">
                        <Beaker className="w-3.5 h-3.5 text-white" />
                      </div>
                    ) : (
                      <div className="w-7 h-7 rounded-full bg-claude-border-light flex items-center justify-center">
                        <User className="w-3.5 h-3.5 text-claude-text-secondary" />
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-claude-text-secondary mb-1.5">
                      {message.role === 'assistant' ? 'RAG Engine' : 'You'}
                    </p>
                    {message.content === '__SUMMARY__' && summaryData ? (
                      <DocumentOverview
                        chunkSummaries={summaryData.chunkSummaries}
                        overallSummary={summaryData.overallSummary}
                        documentName={documentName || 'Document'}
                        latency={summaryData.latency}
                      />
                    ) : (
                      <>
                        <div className="message-content text-chat text-claude-text leading-relaxed whitespace-pre-wrap break-words">
                          {message.content}
                        </div>
                        {message.role === 'assistant' && message.metadata && (
                          <MetadataDisplay metadata={message.metadata} />
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {/* Processing state (upload/summarize) */}
            {isProcessing && (
              <div className="py-5 px-4 bg-claude-surface/40">
                <div className="max-w-chat mx-auto flex gap-4">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-claude-accent to-amber-600 flex items-center justify-center">
                      <Beaker className="w-3.5 h-3.5 text-white" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-claude-text-secondary mb-2.5">RAG Engine</p>
                    <div className="flex items-center gap-3">
                      <div className="w-4 h-4 border-2 border-claude-accent border-t-transparent rounded-full animate-spin" />
                      <span className="text-sm text-claude-text-secondary">{processingLabel}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Loading indicator (asking questions) */}
            {isLoading && !isProcessing && (
              <div className="py-5 px-4 bg-claude-surface/40">
                <div className="max-w-chat mx-auto flex gap-4">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-claude-accent to-amber-600 flex items-center justify-center">
                      <Beaker className="w-3.5 h-3.5 text-white" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-claude-text-secondary mb-2">RAG Engine</p>
                    <div className="flex items-center gap-1.5">
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 p-4 bg-gradient-to-t from-claude-bg via-claude-bg to-transparent">
        <div className="max-w-chat mx-auto">
          <form onSubmit={handleSubmit}>
            <div className="relative bg-claude-input border border-claude-input-border rounded-2xl shadow-lg focus-within:border-claude-text-muted/40 transition-colors">
              {/* Strategy selector inside input */}
              <div className="flex items-center px-4 pt-3 pb-1">
                <div className="flex items-center gap-1.5">
                  <select
                    value={selectedStrategy}
                    onChange={(e) => onStrategyChange(e.target.value as Strategy)}
                    disabled={isLoading}
                    className="bg-transparent text-xs text-claude-text-muted hover:text-claude-text-secondary cursor-pointer focus:outline-none disabled:opacity-50 appearance-none pr-4"
                    style={{ backgroundImage: 'none' }}
                  >
                    {STRATEGIES.map((strategy) => (
                      <option key={strategy.id} value={strategy.id}>
                        {strategy.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="w-3 h-3 text-claude-text-muted -ml-3 pointer-events-none" />
                </div>
              </div>

              {/* Textarea */}
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  disabled
                    ? 'Analyzing document...'
                    : 'Ask about your document...'
                }
                disabled={disabled || isLoading}
                rows={1}
                className="
                  w-full px-4 pb-3 pt-1
                  bg-transparent
                  text-sm text-claude-text placeholder-claude-text-muted
                  focus:outline-none
                  disabled:opacity-50 disabled:cursor-not-allowed
                  resize-none overflow-y-auto
                "
              />

              {/* Send button */}
              <div className="absolute right-2 bottom-2">
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading || disabled}
                  className="
                    p-2 rounded-xl
                    bg-claude-text text-claude-bg
                    hover:bg-white
                    transition-all duration-150
                    disabled:opacity-20 disabled:cursor-not-allowed disabled:hover:bg-claude-text
                  "
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          </form>
          <p className="text-[11px] text-claude-text-muted text-center mt-2">
            Enter to send &middot; Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}
