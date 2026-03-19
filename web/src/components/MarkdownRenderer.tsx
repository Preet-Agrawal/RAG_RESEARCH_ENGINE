'use client';

import { useState, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check } from 'lucide-react';

function CodeBlock({ className, children }: { className?: string; children: string }) {
  const [copied, setCopied] = useState(false);
  const language = className?.replace('language-', '') || '';

  const handleCopy = () => {
    navigator.clipboard.writeText(children.trim());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-3 rounded-xl overflow-hidden bg-[#0d1117] border border-claude-border">
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-claude-border">
        <span className="text-xs text-claude-text-muted font-mono">{language || 'code'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-claude-text-muted hover:text-claude-text transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm leading-relaxed">
        <code className={className}>{children}</code>
      </pre>
    </div>
  );
}

const MarkdownRenderer = memo(function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="markdown-body text-chat text-claude-text leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const isBlock = className || (typeof children === 'string' && children.includes('\n'));
            if (isBlock) {
              return <CodeBlock className={className}>{String(children).replace(/\n$/, '')}</CodeBlock>;
            }
            return (
              <code className="bg-claude-surface px-1.5 py-0.5 rounded text-sm font-mono text-claude-accent" {...props}>
                {children}
              </code>
            );
          },
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto rounded-lg border border-claude-border">
                <table className="w-full text-sm">{children}</table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-claude-surface">{children}</thead>;
          },
          th({ children }) {
            return <th className="px-4 py-2.5 text-left text-xs font-semibold text-claude-text-secondary uppercase tracking-wider border-b border-claude-border">{children}</th>;
          },
          td({ children }) {
            return <td className="px-4 py-2.5 border-b border-claude-border/50 text-claude-text-secondary">{children}</td>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="my-3 pl-4 border-l-2 border-claude-accent/50 text-claude-text-secondary italic">
                {children}
              </blockquote>
            );
          },
          a({ href, children }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-claude-accent hover:text-claude-accent-hover underline underline-offset-2">
                {children}
              </a>
            );
          },
          ul({ children }) {
            return <ul className="my-2 ml-1 space-y-1 list-disc list-inside">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="my-2 ml-1 space-y-1 list-decimal list-inside">{children}</ol>;
          },
          li({ children }) {
            return <li className="text-claude-text-secondary leading-relaxed">{children}</li>;
          },
          h1({ children }) {
            return <h1 className="text-xl font-bold text-claude-text mt-5 mb-3">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="text-lg font-semibold text-claude-text mt-4 mb-2">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="text-base font-semibold text-claude-text mt-3 mb-2">{children}</h3>;
          },
          p({ children }) {
            return <p className="mb-2.5 last:mb-0">{children}</p>;
          },
          strong({ children }) {
            return <strong className="font-semibold text-claude-text">{children}</strong>;
          },
          hr() {
            return <hr className="my-4 border-claude-border" />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});

export default MarkdownRenderer;
