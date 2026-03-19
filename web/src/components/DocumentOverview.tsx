'use client';

import MarkdownRenderer from './MarkdownRenderer';

interface DocumentOverviewProps {
  chunkSummaries: { chunkId: number }[];
  overallSummary: string;
  documentName: string;
  latency?: number;
}

export default function DocumentOverview({
  chunkSummaries,
  overallSummary,
  documentName,
  latency,
}: DocumentOverviewProps) {
  return (
    <div>
      <p className="text-sm font-medium text-claude-text mb-3">
        Document Analysis &mdash; {documentName}
      </p>
      <MarkdownRenderer content={overallSummary} />
      {latency && (
        <p className="text-[11px] text-claude-text-muted mt-3">
          Analyzed {chunkSummaries.length} sections in {latency.toFixed(1)}s
        </p>
      )}
    </div>
  );
}
