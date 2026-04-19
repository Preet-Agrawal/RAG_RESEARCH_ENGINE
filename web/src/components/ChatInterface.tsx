'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, Zap, Clock, Layers, ChevronDown, User, Copy, Check, ArrowDown } from 'lucide-react';
import type { Message, Strategy, ChunkSummary } from '@/types';
import { STRATEGIES } from '@/types';
import DocumentOverview from './DocumentOverview';
import MarkdownRenderer from './MarkdownRenderer';
import SuggestedQuestions from './SuggestedQuestions';
import Logo from './Logo';

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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-claude-surface-hover text-claude-text-muted hover:text-claude-text transition-all" title="Copy">
      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

function MetadataDisplay({ metadata }: { metadata: Message['metadata'] }) {
  if (!metadata) return null;
  const confidence = metadata.confidence;
  const confidenceColor = !confidence ? '' :
    confidence >= 0.75 ? 'bg-emerald-500/15 text-emerald-400' :
    confidence >= 0.5 ? 'bg-yellow-500/15 text-yellow-400' : 'bg-red-500/15 text-red-400';
  const formatStrategy = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="mt-3 pt-3 border-t border-claude-border/30 flex flex-wrap items-center gap-2 text-xs">
      {metadata.confidence !== undefined && (
        <span className={`flex items-center gap-1 px-2 py-1 rounded-full ${confidenceColor}`}>
          <Zap className="w-3 h-3" />{Math.round(metadata.confidence * 100)}%
        </span>
      )}
      {metadata.latency !== undefined && (
        <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-claude-surface text-claude-text-muted">
          <Clock className="w-3 h-3" />{metadata.latency.toFixed(2)}s
        </span>
      )}
      {metadata.chunksProcessed !== undefined && (
        <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-claude-surface text-claude-text-muted">
          <Layers className="w-3 h-3" />{metadata.chunksProcessed} chunks
        </span>
      )}
      {metadata.strategyUsed && (
        <span className="px-2 py-1 rounded-full bg-claude-accent/10 text-claude-accent">
          {formatStrategy(metadata.strategyUsed)}
        </span>
      )}
    </div>
  );
}

function ShimmerLoader() {
  return (
    <div className="space-y-3">
      <div className="h-3.5 shimmer-bar rounded-md w-full" />
      <div className="h-3.5 shimmer-bar rounded-md w-[92%]" />
      <div className="h-3.5 shimmer-bar rounded-md w-[75%]" />
      <div className="h-3.5 shimmer-bar rounded-md w-[60%]" />
    </div>
  );
}

// Streaming: show plain text word-by-word, then swap to markdown when done
function StreamingMessage({ content, isNew }: { content: string; isNew: boolean }) {
  const [displayedCount, setDisplayedCount] = useState(isNew ? 0 : -1); // -1 = done
  const wordsRef = useRef<string[]>([]);

  useEffect(() => {
    if (!isNew) {
      setDisplayedCount(-1);
      return;
    }
    wordsRef.current = content.split(/(\s+)/);
    setDisplayedCount(0);

    let i = 0;
    const total = wordsRef.current.length;
    const interval = setInterval(() => {
      i += 4; // 4 tokens per tick
      if (i >= total) {
        setDisplayedCount(-1);
        clearInterval(interval);
      } else {
        setDisplayedCount(i);
      }
    }, 15);

    return () => clearInterval(interval);
  }, [content, isNew]);

  // Done streaming -> render with markdown
  if (displayedCount === -1) {
    return <MarkdownRenderer content={content} />;
  }

  // Still streaming -> render plain text (fast, no markdown parsing)
  const partial = wordsRef.current.slice(0, displayedCount).join('');
  return (
    <div className="text-chat text-claude-text leading-relaxed whitespace-pre-wrap break-words">
      {partial}
      <span className="inline-block w-1.5 h-4 bg-claude-accent/70 rounded-sm animate-pulse ml-0.5 align-text-bottom" />
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
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [newestMsgId, setNewestMsgId] = useState<string | null>(null);
  const prevLenRef = useRef(messages.length);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Detect new assistant message
  useEffect(() => {
    if (messages.length > prevLenRef.current) {
      const last = messages[messages.length - 1];
      if (last.role === 'assistant' && last.content !== '__SUMMARY__') {
        setNewestMsgId(last.id);
      }
    }
    prevLenRef.current = messages.length;
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [input]);

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    setShowScrollButton(el.scrollHeight - el.scrollTop - el.clientHeight > 200);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;
    const msg = input.trim();
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    await onSendMessage(msg);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const userMessageCount = messages.filter(m => m.role === 'user').length;
  const showSuggestions = summaryData && userMessageCount === 0 && !isLoading && !isProcessing;

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto" ref={scrollContainerRef} onScroll={handleScroll}>
        {messages.length === 0 && !isProcessing ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md px-6">
              <div className="flex justify-center mb-4">
                <Logo size={48} />
              </div>
              <h2 className="text-lg font-semibold text-claude-text mb-2">Ask about your document</h2>
              <p className="text-sm text-claude-text-muted leading-relaxed">
                Your document is loaded. Ask any question and the selected recovery strategy will help find answers even from the middle sections.
              </p>
            </div>
          </div>
        ) : (
          <div className="pb-4">
            {messages.map((message) => (
              <div key={message.id} className={`group py-5 px-4 ${message.role === 'user' ? 'bg-transparent' : 'bg-claude-assistant-msg'}`}>
                <div className="max-w-chat mx-auto flex gap-4">
                  <div className="flex-shrink-0 mt-0.5">
                    {message.role === 'assistant' ? (
                      <Logo size={28} className="flex-shrink-0" />
                    ) : (
                      <div className="w-7 h-7 rounded-full bg-claude-border-light flex items-center justify-center">
                        <User className="w-3.5 h-3.5 text-claude-text-secondary" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-xs font-medium text-claude-text-secondary">
                        {message.role === 'assistant' ? 'RAG Engine' : 'You'}
                      </p>
                      {message.role === 'assistant' && message.content !== '__SUMMARY__' && (
                        <CopyButton text={message.content} />
                      )}
                    </div>
                    {message.content === '__SUMMARY__' && summaryData ? (
                      <>
                        <DocumentOverview
                          chunkSummaries={summaryData.chunkSummaries}
                          overallSummary={summaryData.overallSummary}
                          documentName={documentName || 'Document'}
                          latency={summaryData.latency}
                        />
                        {showSuggestions && (
                          <SuggestedQuestions
                            overallSummary={summaryData.overallSummary}
                            chunkSummaries={summaryData.chunkSummaries}
                            onSelectQuestion={(q) => onSendMessage(q)}
                          />
                        )}
                      </>
                    ) : message.role === 'assistant' ? (
                      <>
                        <StreamingMessage content={message.content} isNew={message.id === newestMsgId} />
                        {message.metadata && <MetadataDisplay metadata={message.metadata} />}
                      </>
                    ) : (
                      <div className="text-chat text-claude-text leading-relaxed whitespace-pre-wrap break-words">
                        {message.content}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {isProcessing && (
              <div className="py-5 px-4 bg-claude-assistant-msg">
                <div className="max-w-chat mx-auto flex gap-4">
                  <div className="flex-shrink-0 mt-0.5">
                    <Logo size={28} className="flex-shrink-0" />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-claude-text-secondary mb-2.5">RAG Engine</p>
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-4 h-4 border-2 border-claude-accent border-t-transparent rounded-full animate-spin" />
                      <span className="text-sm text-claude-text-secondary">{processingLabel}</span>
                    </div>
                    <ShimmerLoader />
                  </div>
                </div>
              </div>
            )}

            {isLoading && !isProcessing && (
              <div className="py-5 px-4 bg-claude-assistant-msg">
                <div className="max-w-chat mx-auto flex gap-4">
                  <div className="flex-shrink-0 mt-0.5">
                    <Logo size={28} className="flex-shrink-0" />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-claude-text-secondary mb-2">RAG Engine</p>
                    <ShimmerLoader />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Scroll to bottom */}
      {showScrollButton && (
        <div className="flex justify-center -mt-10 relative z-10">
          <button onClick={scrollToBottom} className="p-2 bg-claude-surface border border-claude-border rounded-full shadow-lg hover:bg-claude-surface-hover transition-all">
            <ArrowDown className="w-4 h-4 text-claude-text-secondary" />
          </button>
        </div>
      )}

      {/* Input */}
      <div className="flex-shrink-0 p-4 bg-gradient-to-t from-claude-bg via-claude-bg to-transparent">
        <div className="max-w-chat mx-auto">
          <form onSubmit={handleSubmit}>
            <div className="relative bg-claude-input border border-claude-input-border rounded-2xl shadow-lg focus-within:border-claude-text-muted/40 transition-colors">
              <div className="flex items-center px-4 pt-3 pb-1">
                <div className="flex items-center gap-1.5">
                  <select
                    value={selectedStrategy}
                    onChange={(e) => onStrategyChange(e.target.value as Strategy)}
                    disabled={isLoading}
                    className="bg-transparent text-xs text-claude-text-muted hover:text-claude-text-secondary cursor-pointer focus:outline-none disabled:opacity-50 appearance-none pr-4"
                    style={{ backgroundImage: 'none' }}
                  >
                    {STRATEGIES.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                  <ChevronDown className="w-3 h-3 text-claude-text-muted -ml-3 pointer-events-none" />
                </div>
              </div>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={disabled ? 'Analyzing document...' : 'Ask about your document...'}
                disabled={disabled || isLoading}
                rows={1}
                className="w-full px-4 pb-3 pt-1 bg-transparent text-sm text-claude-text placeholder-claude-text-muted focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed resize-none overflow-y-auto"
              />
              <div className="absolute right-2 bottom-2">
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading || disabled}
                  className="p-2 rounded-xl bg-claude-text text-claude-bg hover:opacity-80 transition-all duration-150 disabled:opacity-20 disabled:cursor-not-allowed"
                >
                  {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
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
