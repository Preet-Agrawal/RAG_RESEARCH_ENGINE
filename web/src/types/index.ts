export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface PDFDocument {
  file: File;
  name: string;
  size: number;
  uploadedAt: Date;
}

export interface RAGResponse {
  answer: string;
  sources: string[];
  confidence: number;
  positions: {
    position: number;
    accuracy: number;
  }[];
}

export interface AnalysisResult {
  success: boolean;
  response?: RAGResponse;
  error?: string;
}
