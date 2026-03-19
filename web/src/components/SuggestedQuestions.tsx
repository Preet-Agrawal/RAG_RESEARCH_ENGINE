'use client';

import { useMemo } from 'react';
import { Sparkles } from 'lucide-react';
import type { ChunkSummary } from '@/types';

interface SuggestedQuestionsProps {
  overallSummary: string;
  chunkSummaries: ChunkSummary[];
  onSelectQuestion: (question: string) => void;
}

function extractKeyTerms(text: string): string[] {
  // Extract capitalized multi-word phrases and notable terms
  const matches = text.match(/[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+/g) || [];
  // Also get quoted terms
  const quoted = text.match(/"([^"]+)"/g)?.map((q) => q.replace(/"/g, '')) || [];
  // Get terms after colons or dashes
  const afterColon = text.match(/(?::|–|-)\s*([A-Z][^.,:;]+)/g)?.map((m) => m.replace(/^(?::|–|-)\s*/, '')) || [];

  const all = Array.from(new Set([...matches, ...quoted, ...afterColon]));
  return all.filter((t) => t.length > 3 && t.length < 60).slice(0, 5);
}

export default function SuggestedQuestions({
  overallSummary,
  chunkSummaries,
  onSelectQuestion,
}: SuggestedQuestionsProps) {
  const questions = useMemo(() => {
    const result: string[] = [];

    // Always include a general question
    result.push('What are the main topics and key findings in this document?');

    // Extract a question from middle-zone chunks (the "lost" content)
    const middleChunks = chunkSummaries.filter((c) => c.isMiddle);
    if (middleChunks.length > 0) {
      const middleTerms = extractKeyTerms(middleChunks.map((c) => c.summary).join(' '));
      if (middleTerms.length > 0) {
        result.push(`What does the document say about ${middleTerms[0]}?`);
      } else {
        result.push('What details are covered in the middle sections of this document?');
      }
    }

    // Extract a question from overall summary key terms
    const summaryTerms = extractKeyTerms(overallSummary);
    if (summaryTerms.length > 1) {
      result.push(`Explain the relationship between ${summaryTerms[0]} and ${summaryTerms[1]}`);
    } else if (summaryTerms.length === 1) {
      result.push(`What is the significance of ${summaryTerms[0]} in this document?`);
    }

    // Add a conclusions/recommendations question
    result.push('What are the conclusions or recommendations from this document?');

    return result.slice(0, 4);
  }, [overallSummary, chunkSummaries]);

  return (
    <div className="mt-5">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-3.5 h-3.5 text-claude-accent" />
        <span className="text-xs font-medium text-claude-text-muted">Suggested questions</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelectQuestion(q)}
            className="px-3.5 py-2 rounded-xl border border-claude-border bg-claude-surface hover:bg-claude-surface-hover hover:border-claude-accent/40 text-sm text-claude-text-secondary hover:text-claude-text transition-all duration-150 text-left"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
