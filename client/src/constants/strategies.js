export const STRATEGIES = [
  {
    id: 'para',
    name: 'PARA (Position-Aware Retrieval)',
    description: 'Semantic embedding retrieval with position-bias correction',
    recommended: true,
  },
  {
    id: 'combined',
    name: 'Combined',
    description: 'Uses all prompt strategies together for best middle-content recovery',
    recommended: true,
  },
  {
    id: 'reranking',
    name: 'Reranking Prompt',
    description: 'Places most relevant chunks first and last',
  },
  {
    id: 'chunk_by_chunk_reasoning',
    name: 'Chunk-by-Chunk Reasoning',
    description: 'Evaluates each passage individually before synthesizing',
  },
  {
    id: 'map_reduce',
    name: 'Map-Reduce',
    description: 'Extracts relevant facts per chunk, then synthesizes',
  },
  {
    id: 'attention_anchoring',
    name: 'Attention Anchoring',
    description: 'Markers and instructions to force attention on middle content',
  },
  {
    id: 'relevance_restructuring',
    name: 'Relevance Restructuring',
    description: 'Reorganizes content to place relevant sections at edges',
  },
  {
    id: 'query_aware_compression',
    name: 'Query-Aware Compression',
    description: 'Compresses irrelevant content, expands relevant content',
  },
  {
    id: 'query_aware_contextualization',
    name: 'Query-Aware Contextualization',
    description: 'Query before AND after documents (Liu et al. 2023)',
  },
  {
    id: 'chunked_reading',
    name: 'Chunked Reading',
    description: 'Processes document in smaller chunks',
  },
  {
    id: 'baseline',
    name: 'Baseline (Standard)',
    description: 'Standard processing without middle-content recovery',
  },
];
