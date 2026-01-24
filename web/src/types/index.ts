export type Strategy =
  | 'combined'
  | 'baseline'
  | 'attention_anchoring'
  | 'relevance_restructuring'
  | 'chunked_reading';

export interface StrategyInfo {
  id: Strategy;
  name: string;
  description: string;
  recommended?: boolean;
}

export const STRATEGIES: StrategyInfo[] = [
  {
    id: 'combined',
    name: 'Combined (Recommended)',
    description: 'Uses all strategies together for best middle-content recovery',
    recommended: true,
  },
  {
    id: 'attention_anchoring',
    name: 'Attention Anchoring',
    description: 'Uses markers and instructions to force attention on middle content',
  },
  {
    id: 'relevance_restructuring',
    name: 'Relevance Restructuring',
    description: 'Reorganizes content to place relevant sections at document edges',
  },
  {
    id: 'chunked_reading',
    name: 'Chunked Reading',
    description: 'Processes document in smaller chunks to avoid middle-content loss',
  },
  {
    id: 'baseline',
    name: 'Baseline (Standard)',
    description: 'Standard processing without middle-content recovery (for comparison)',
  },
];

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    strategyUsed?: string;
    confidence?: number;
    latency?: number;
    chunksProcessed?: number;
    strategyExplanation?: string;
  };
}

export interface PDFDocument {
  file: File;
  name: string;
  size: number;
  uploadedAt: Date;
}

export interface RAGResponse {
  success: boolean;
  answer: string;
  sources: string[];
  confidence: number;
  strategyUsed: string;
  chunksProcessed: number;
  latency: number;
  strategyExplanation: string;
  error?: string;
}
