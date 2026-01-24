'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import type { Message } from '@/types';

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (message: string) => Promise<void>;
  isLoading?: boolean;
  disabled?: boolean;
}

export default function ChatInterface({
  messages,
  onSendMessage,
  isLoading = false,
  disabled = false,
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

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <h2 className="text-2xl font-semibold text-claude-text mb-2">
                RAG Research Engine
              </h2>
              <p className="text-claude-text-secondary">
                Upload a PDF document and ask questions to test the "Lost in the Middle" phenomenon
              </p>
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
                    max-w-[80%] rounded-2xl px-4 py-3
                    ${message.role === 'user'
                      ? 'bg-claude-accent text-white'
                      : 'bg-claude-surface text-claude-text border border-claude-border'
                    }
                  `}
                >
                  <div className="whitespace-pre-wrap break-words">
                    {message.content}
                  </div>
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
                  <Loader2 className="w-5 h-5 animate-spin text-claude-accent" />
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
