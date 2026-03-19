'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ChunkSummary } from '@/types';
import MarkdownRenderer from './MarkdownRenderer';

interface DocumentOverviewProps {
  chunkSummaries: ChunkSummary[];
  overallSummary: string;
  documentName: string;
  latency?: number;
}

const zoneConfig = {
  beginning: { color: 'border-l-emerald-500', bg: 'bg-emerald-500/5', badge: 'bg-emerald-500/15 text-emerald-400', label: 'Start' },
  middle: { color: 'border-l-orange-500', bg: 'bg-orange-500/5', badge: 'bg-orange-500/15 text-orange-400', label: 'Middle' },
  end: { color: 'border-l-blue-500', bg: 'bg-blue-500/5', badge: 'bg-blue-500/15 text-blue-400', label: 'End' },
};

export default function DocumentOverview({
  chunkSummaries,
  overallSummary,
  documentName,
  latency,
}: DocumentOverviewProps) {
  const [expanded, setExpanded] = useState(false);

  const beginCount = chunkSummaries.filter(c => c.zone === 'beginning').length;
  const middleCount = chunkSummaries.filter(c => c.zone === 'middle').length;
  const endCount = chunkSummaries.filter(c => c.zone === 'end').length;

  // Show first 3 + middle chunks when collapsed, all when expanded
  const displayChunks = expanded
    ? chunkSummaries
    : chunkSummaries.slice(0, 4);

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div>
        <p className="text-sm font-semibold text-claude-text mb-3">
          Document Analysis &mdash; {documentName}
        </p>
        <MarkdownRenderer content={overallSummary} />
      </div>

      {/* Zone legend */}
      <div className="flex items-center gap-4 text-[11px]">
        <span className="text-claude-text-muted font-medium">{chunkSummaries.length} chunks</span>
        <span className="w-px h-3 bg-claude-border" />
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-sm bg-emerald-500" />
          <span className="text-claude-text-muted">Start ({beginCount})</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-sm bg-orange-500" />
          <span className="text-claude-text-muted">Middle ({middleCount})</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-sm bg-blue-500" />
          <span className="text-claude-text-muted">End ({endCount})</span>
        </span>
      </div>

      {/* Chunk list */}
      <div className="space-y-1.5">
        {displayChunks.map((chunk) => {
          const cfg = zoneConfig[chunk.zone] || zoneConfig.beginning;
          return (
            <div key={chunk.chunkId} className={`p-3 rounded-lg border-l-2 ${cfg.color} ${cfg.bg}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-claude-text">
                  Chunk {chunk.chunkId}/{chunk.totalChunks}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-claude-text-muted">{chunk.position}%</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${cfg.badge}`}>
                    {cfg.label}
                  </span>
                </div>
              </div>
              <p className="text-xs text-claude-text-secondary leading-relaxed">{chunk.summary}</p>
            </div>
          );
        })}
      </div>

      {/* Show more/less */}
      {chunkSummaries.length > 4 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-claude-accent hover:text-claude-accent-hover transition-colors"
        >
          {expanded ? (
            <>Show less <ChevronUp className="w-3 h-3" /></>
          ) : (
            <>Show all {chunkSummaries.length} chunks <ChevronDown className="w-3 h-3" /></>
          )}
        </button>
      )}

      {latency && (
        <p className="text-[11px] text-claude-text-muted">
          Analyzed in {latency.toFixed(1)}s
        </p>
      )}
    </div>
  );
}
