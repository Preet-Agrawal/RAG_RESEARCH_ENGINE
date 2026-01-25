'use client';

import { useState } from 'react';
import PDFUploader from '@/components/PDFUploader';
import ChatInterface from '@/components/ChatInterface';
import { Beaker, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import type { Message, PDFDocument, Strategy, RAGResponse, ChunkSummary, SummarizeResponse } from '@/types';
import axios from 'axios';

export default function Home() {
  const [currentDocument, setCurrentDocument] = useState<PDFDocument | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy>('combined');
  const [chunkSummaries, setChunkSummaries] = useState<ChunkSummary[]>([]);
  const [showAllChunks, setShowAllChunks] = useState(false);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.success) {
        setCurrentDocument({
          file,
          name: file.name,
          size: file.size,
          uploadedAt: new Date(),
        });
        setUploadedFilename(response.data.filename);
        setIsUploading(false);

        // Now summarize the document
        setIsSummarizing(true);
        setMessages([
          {
            id: Date.now().toString(),
            role: 'assistant',
            content: `PDF "${file.name}" uploaded! Analyzing all sections with special focus on middle content...`,
            timestamp: new Date(),
          },
        ]);

        try {
          const summarizeResponse = await axios.post<SummarizeResponse>('/api/summarize', {
            filename: response.data.filename,
          });

          if (summarizeResponse.data.success) {
            setChunkSummaries(summarizeResponse.data.chunkSummaries);

            const middleCount = summarizeResponse.data.middleChunksCount;
            const totalCount = summarizeResponse.data.totalChunks;

            setMessages([
              {
                id: Date.now().toString(),
                role: 'assistant',
                content: `Document analyzed! Found ${totalCount} sections (${middleCount} in the critical middle zone).\n\n**Overall Summary:**\n${summarizeResponse.data.overallSummary}\n\nYou can now ask questions. The chunk summaries below show what's in each section - pay attention to the MIDDLE sections highlighted in orange!`,
                timestamp: new Date(),
                metadata: {
                  latency: summarizeResponse.data.latency,
                  chunksProcessed: totalCount,
                },
              },
            ]);
          }
        } catch (error) {
          console.error('Summarize failed:', error);
          setMessages([
            {
              id: Date.now().toString(),
              role: 'assistant',
              content: `PDF uploaded but couldn't generate summary. You can still ask questions about the document.`,
              timestamp: new Date(),
            },
          ]);
        } finally {
          setIsSummarizing(false);
        }
      }
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Failed to upload PDF. Please try again.');
      setIsUploading(false);
    }
  };

  const handleRemoveDocument = () => {
    setCurrentDocument(null);
    setUploadedFilename('');
    setMessages([]);
    setChunkSummaries([]);
  };

  const handleSendMessage = async (messageText: string) => {
    if (!uploadedFilename) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);
    try {
      const response = await axios.post<RAGResponse>('/api/ask', {
        question: messageText,
        filename: uploadedFilename,
        strategy: selectedStrategy,
      });

      if (response.data.success) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.data.answer,
          timestamp: new Date(),
          metadata: {
            strategyUsed: response.data.strategyUsed,
            confidence: response.data.confidence,
            latency: response.data.latency,
            chunksProcessed: response.data.chunksProcessed,
            strategyExplanation: response.data.strategyExplanation,
          },
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        throw new Error(response.data.error || 'Unknown error');
      }
    } catch (error: any) {
      console.error('Ask failed:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.response?.data?.error || error.message}. Please try again.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStrategyChange = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
  };

  const getZoneColor = (zone: string, isMiddle: boolean) => {
    if (isMiddle) return 'border-orange-500 bg-orange-500/10';
    if (zone === 'beginning') return 'border-green-500 bg-green-500/10';
    return 'border-blue-500 bg-blue-500/10';
  };

  const getZoneLabel = (zone: string) => {
    if (zone === 'middle') return 'MIDDLE (Critical)';
    if (zone === 'beginning') return 'Beginning';
    return 'End';
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-claude-surface border-b border-claude-border px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-claude-accent/10 rounded-lg">
              <Beaker className="w-6 h-6 text-claude-accent" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-claude-text">
                RAG Research Engine
              </h1>
              <p className="text-sm text-claude-text-secondary">
                Lost in the Middle Recovery
              </p>
            </div>
          </div>
          <div className="px-3 py-1 bg-claude-accent/10 border border-claude-accent/20 rounded-full">
            <span className="text-xs font-medium text-claude-accent">
              {currentDocument ? 'Document Loaded' : 'No Document'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-7xl mx-auto px-6 py-6">
          {currentDocument ? (
            <div className="h-full flex gap-4">
              {/* Left Panel - Chunk Summaries */}
              <div className="w-80 flex-shrink-0 flex flex-col gap-4 overflow-hidden">
                <PDFUploader
                  onUpload={handleUpload}
                  currentDocument={currentDocument}
                  onRemove={handleRemoveDocument}
                />

                {/* Chunk Summaries Panel */}
                {chunkSummaries.length > 0 && (
                  <div className="flex-1 bg-claude-surface border border-claude-border rounded-lg overflow-hidden flex flex-col">
                    <div className="p-3 border-b border-claude-border bg-claude-surface/50">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-medium text-claude-text flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          Chunk Summaries
                        </h3>
                        <button
                          onClick={() => setShowAllChunks(!showAllChunks)}
                          className="text-xs text-claude-accent hover:underline flex items-center gap-1"
                        >
                          {showAllChunks ? 'Show Less' : 'Show All'}
                          {showAllChunks ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                      </div>
                      <p className="text-xs text-claude-text-secondary mt-1">
                        Orange = Middle sections (often missed by LLMs)
                      </p>
                    </div>
                    <div className="flex-1 overflow-y-auto p-3 space-y-2">
                      {(showAllChunks ? chunkSummaries : chunkSummaries.filter(c => c.isMiddle || c.chunkId <= 2 || c.chunkId >= chunkSummaries.length - 1)).map((chunk) => (
                        <div
                          key={chunk.chunkId}
                          className={`p-2 rounded-lg border ${getZoneColor(chunk.zone, chunk.isMiddle)}`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-claude-text">
                              Section {chunk.chunkId}/{chunk.totalChunks}
                            </span>
                            <span className={`text-xs px-1.5 py-0.5 rounded ${chunk.isMiddle ? 'bg-orange-500/20 text-orange-400' : 'bg-claude-bg text-claude-text-secondary'}`}>
                              {getZoneLabel(chunk.zone)}
                            </span>
                          </div>
                          <p className="text-xs text-claude-text-secondary line-clamp-3">
                            {chunk.summary}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Right Panel - Chat */}
              <div className="flex-1 min-w-0 bg-claude-surface/30 border border-claude-border rounded-lg">
                <ChatInterface
                  messages={messages}
                  onSendMessage={handleSendMessage}
                  isLoading={isLoading || isSummarizing}
                  disabled={!currentDocument || isSummarizing}
                  selectedStrategy={selectedStrategy}
                  onStrategyChange={handleStrategyChange}
                />
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="max-w-2xl w-full">
                {isUploading ? (
                  <div className="text-center">
                    <div className="inline-block p-4 bg-claude-surface rounded-full mb-4">
                      <div className="w-8 h-8 border-4 border-claude-accent border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    <p className="text-claude-text">Uploading PDF...</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="text-center mb-8">
                      <div className="inline-flex items-center justify-center p-3 bg-claude-accent/10 rounded-xl mb-4">
                        <Beaker className="w-10 h-10 text-claude-accent" />
                      </div>
                      <h2 className="text-2xl font-semibold text-claude-text mb-2">
                        Lost in the Middle Recovery
                      </h2>
                      <p className="text-claude-text-secondary max-w-md mx-auto">
                        Upload a PDF to get summaries of ALL sections, especially the middle ones that LLMs typically ignore.
                      </p>
                    </div>
                    <PDFUploader onUpload={handleUpload} />
                    <div className="bg-claude-surface border border-claude-border rounded-lg p-4">
                      <h3 className="text-sm font-medium text-claude-text mb-3">
                        What happens when you upload:
                      </h3>
                      <ol className="space-y-2 text-sm text-claude-text-secondary">
                        <li className="flex gap-2">
                          <span className="text-claude-accent font-medium">1.</span>
                          Document is split into chunks with position tracking
                        </li>
                        <li className="flex gap-2">
                          <span className="text-claude-accent font-medium">2.</span>
                          Each chunk is summarized (middle chunks get extra attention)
                        </li>
                        <li className="flex gap-2">
                          <span className="text-claude-accent font-medium">3.</span>
                          Overall summary is generated from all sections
                        </li>
                        <li className="flex gap-2">
                          <span className="text-claude-accent font-medium">4.</span>
                          You can ask questions with middle-recovery strategies
                        </li>
                      </ol>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-claude-surface border-t border-claude-border px-6 py-3">
        <div className="max-w-7xl mx-auto text-center text-xs text-claude-text-secondary">
          Powered by Groq (Llama 3.1) | Focusing on Middle Content Recovery
        </div>
      </footer>
    </div>
  );
}
