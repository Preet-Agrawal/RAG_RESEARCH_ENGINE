export type Strategy =
  | 'combined'
  | 'baseline'
  | 'attention_anchoring'
  | 'relevance_restructuring'
  | 'query_aware_compression'
  | 'query_aware_contextualization'
  | 'chunked_reading'
  | 'reranking'
  | 'chunk_by_chunk_reasoning'
  | 'map_reduce';

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
    id: 'reranking',
    name: 'Reranking Prompt',
    description: 'Places most relevant chunks first and last with explicit equal-attention instructions',
  },
  {
    id: 'chunk_by_chunk_reasoning',
    name: 'Chunk-by-Chunk Reasoning',
    description: 'Evaluates each passage individually before synthesizing, with passage citations',
  },
  {
    id: 'map_reduce',
    name: 'Map-Reduce',
    description: 'Extracts relevant facts per chunk (map), then combines them into a final answer (reduce)',
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
    id: 'query_aware_compression',
    name: 'Query-Aware Compression',
    description: 'Compresses irrelevant content, expands relevant content at attention-rich positions',
  },
  {
    id: 'query_aware_contextualization',
    name: 'Query-Aware Contextualization',
    description: 'Query before AND after documents (Liu et al. 2023 paper technique)',
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

export interface ChunkSummary {
  chunkId: number;
  totalChunks: number;
  zone: 'beginning' | 'middle' | 'end';
  position: number;
  summary: string;
  isMiddle: boolean;
}

export interface SummarizeResponse {
  success: boolean;
  totalChunks: number;
  chunkSummaries: ChunkSummary[];
  overallSummary: string;
  middleChunksCount: number;
  latency: number;
  error?: string;
}

// Strategy Comparison Types
export interface StrategyComparisonResult {
  strategy: string;
  answer: string;
  confidence: number;
  latency: number;
  chunksProcessed: number;
  explanation: string;
}

export interface CompareResponse {
  success: boolean;
  question: string;
  comparison: StrategyComparisonResult[];
  bestStrategy: string;
  totalLatency: number;
  error?: string;
}

// Benchmark Types
export interface BenchmarkPositionResult {
  positionPercent: number;
  positionZone: 'beginning' | 'middle' | 'end';
  baselineFound: boolean;
  baselineConfidence: number;
  combinedFound: boolean;
  combinedConfidence: number;
  recoverySuccess: boolean;
}

export interface BenchmarkSummary {
  baselineAccuracy: number;
  combinedAccuracy: number;
  improvement: number;
  deadZonePositions: number[];
  deadZoneRecoveryRate: number;
}

export interface BenchmarkResponse {
  success: boolean;
  needleFact: string;
  testPositions: number[];
  results: BenchmarkPositionResult[];
  summary: BenchmarkSummary;
  totalLatency: number;
  error?: string;
}
