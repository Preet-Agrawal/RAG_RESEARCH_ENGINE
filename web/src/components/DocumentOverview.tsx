'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ChunkSummary } from '@/types';

interface DocumentOverviewProps {
  chunkSummaries: ChunkSummary[];
  overallSummary: string;
  documentName: string;
  latency?: number;
}

function AttentionChart({ chunks }: { chunks: ChunkSummary[] }) {
  const total = chunks.length;
  if (total === 0) return null;

  const beginCount = chunks.filter(c => c.zone === 'beginning').length;
  const middleCount = chunks.filter(c => c.zone === 'middle').length;
  const endCount = chunks.filter(c => c.zone === 'end').length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-claude-text-muted">
        <span>Document Position Map</span>
        <span>{total} sections</span>
      </div>

      <div className="flex gap-[2px] h-10 items-end">
        {chunks.map((chunk, i) => {
          const barColor = chunk.zone === 'middle'
            ? 'bg-orange-500'
            : chunk.zone === 'beginning'
            ? 'bg-emerald-500'
            : 'bg-blue-500';

          const pos = i / (total - 1 || 1);
          const attention = 0.4 + 0.6 * Math.abs(2 * pos - 1);
          const height = Math.max(20, attention * 100);

          return (
            <div key={chunk.chunkId} className="group relative flex-1 flex items-end">
              <div
                className={`w-full rounded-t-sm ${barColor} opacity-70 group-hover:opacity-100 transition-opacity cursor-pointer`}
                style={{ height: `${height}%` }}
              />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10 w-52 pointer-events-none">
                <div className="bg-claude-bg border border-claude-border rounded-lg p-2.5 shadow-xl text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-claude-text">Section {chunk.chunkId}</span>
                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${
                      chunk.isMiddle
                        ? 'bg-orange-500/15 text-orange-400'
                        : chunk.zone === 'beginning'
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : 'bg-blue-500/15 text-blue-400'
                    }`}>
                      {chunk.zone}
                    </span>
                  </div>
                  <p className="text-claude-text-secondary leading-relaxed line-clamp-3">{chunk.summary}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-3 text-[11px]">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />
          <span className="text-claude-text-muted">Start ({beginCount})</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-orange-500" />
          <span className="text-claude-text-muted">Middle ({middleCount})</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-blue-500" />
          <span className="text-claude-text-muted">End ({endCount})</span>
        </span>
      </div>
    </div>
  );
}

function ChunkDetail({ chunk }: { chunk: ChunkSummary }) {
  const borderColor = chunk.isMiddle
    ? 'border-l-orange-500'
    : chunk.zone === 'beginning'
    ? 'border-l-emerald-500'
    : 'border-l-blue-500';

  const bgColor = chunk.isMiddle
    ? 'bg-orange-500/5'
    : chunk.zone === 'beginning'
    ? 'bg-emerald-500/5'
    : 'bg-blue-500/5';

  return (
    <div className={`p-3 rounded-lg border-l-2 ${borderColor} ${bgColor}`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-medium text-claude-text">
          Section {chunk.chunkId}/{chunk.totalChunks}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-claude-text-muted">{chunk.position}%</span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
            chunk.isMiddle
              ? 'bg-orange-500/15 text-orange-400'
              : chunk.zone === 'beginning'
              ? 'bg-emerald-500/15 text-emerald-400'
              : 'bg-blue-500/15 text-blue-400'
          }`}>
            {chunk.zone}
          </span>
        </div>
      </div>
      <p className="text-xs text-claude-text-secondary leading-relaxed">{chunk.summary}</p>
    </div>
  );
}

export default function DocumentOverview({
  chunkSummaries,
  overallSummary,
  documentName,
  latency,
}: DocumentOverviewProps) {
  const [showAllChunks, setShowAllChunks] = useState(false);

  const displayChunks = showAllChunks
    ? chunkSummaries
    : chunkSummaries.filter(c => c.isMiddle || c.chunkId <= 2 || c.chunkId >= chunkSummaries.length - 1);

  return (
    <div className="space-y-5">
      {/* Summary - always visible */}
      <div>
        <p className="text-sm font-medium text-claude-text mb-2">
          Document Analysis &mdash; {documentName}
        </p>
        <p className="text-chat text-claude-text leading-relaxed">{overallSummary}</p>
      </div>

      {/* Chart - always visible */}
      <div className="p-4 bg-claude-surface/60 border border-claude-border rounded-xl">
        <AttentionChart chunks={chunkSummaries} />
      </div>

      {/* All section summaries */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-semibold text-claude-text-muted uppercase tracking-wider">
            Section-by-Section Analysis ({chunkSummaries.length})
          </p>
          {chunkSummaries.length > displayChunks.length && !showAllChunks && (
            <button
              onClick={() => setShowAllChunks(true)}
              className="text-xs text-claude-accent hover:text-claude-accent-hover transition-colors flex items-center gap-0.5"
            >
              Show all <ChevronDown className="w-3 h-3" />
            </button>
          )}
          {showAllChunks && (
            <button
              onClick={() => setShowAllChunks(false)}
              className="text-xs text-claude-accent hover:text-claude-accent-hover transition-colors flex items-center gap-0.5"
            >
              Show less <ChevronUp className="w-3 h-3" />
            </button>
          )}
        </div>
        <div className="space-y-1.5">
          {displayChunks.map(chunk => (
            <ChunkDetail key={chunk.chunkId} chunk={chunk} />
          ))}
        </div>
      </div>

      {latency && (
        <p className="text-[11px] text-claude-text-muted">
          Analyzed in {latency.toFixed(1)}s
        </p>
      )}
    </div>
  );
}
