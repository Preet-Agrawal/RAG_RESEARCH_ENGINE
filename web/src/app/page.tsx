'use client';

import { useState } from 'react';
import PDFUploader from '@/components/PDFUploader';
import ChatInterface from '@/components/ChatInterface';
import { Beaker, FileText, ChevronDown, ChevronUp, GitCompare, FlaskConical, X, BarChart3 } from 'lucide-react';
import type { Message, PDFDocument, Strategy, RAGResponse, ChunkSummary, SummarizeResponse, CompareResponse, BenchmarkResponse } from '@/types';
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
  const [showCompareModal, setShowCompareModal] = useState(false);
  const [showBenchmarkModal, setShowBenchmarkModal] = useState(false);
  const [compareResults, setCompareResults] = useState<CompareResponse | null>(null);
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkResponse | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [isBenchmarking, setIsBenchmarking] = useState(false);
  const [compareQuestion, setCompareQuestion] = useState('');

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

  const handleCompareStrategies = async () => {
    if (!uploadedFilename || !compareQuestion.trim()) return;

    setIsComparing(true);
    setCompareResults(null);

    try {
      const response = await axios.post<CompareResponse>('/api/compare', {
        question: compareQuestion,
        filename: uploadedFilename,
      });

      if (response.data.success) {
        setCompareResults(response.data);
      }
    } catch (error: any) {
      console.error('Compare failed:', error);
      alert('Failed to compare strategies: ' + (error.response?.data?.error || error.message));
    } finally {
      setIsComparing(false);
    }
  };

  const handleRunBenchmark = async () => {
    if (!uploadedFilename) return;

    setIsBenchmarking(true);
    setBenchmarkResults(null);

    try {
      const response = await axios.post<BenchmarkResponse>('/api/benchmark', {
        filename: uploadedFilename,
      });

      if (response.data.success) {
        setBenchmarkResults(response.data);
      }
    } catch (error: any) {
      console.error('Benchmark failed:', error);
      alert('Failed to run benchmark: ' + (error.response?.data?.error || error.message));
    } finally {
      setIsBenchmarking(false);
    }
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
          <div className="flex items-center gap-3">
            {currentDocument && (
              <>
                <button
                  onClick={() => setShowCompareModal(true)}
                  className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/10 border border-purple-500/30 rounded-lg text-sm text-purple-400 hover:bg-purple-500/20 transition-colors"
                >
                  <GitCompare className="w-4 h-4" />
                  Compare Strategies
                </button>
                <button
                  onClick={() => setShowBenchmarkModal(true)}
                  className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/30 rounded-lg text-sm text-green-400 hover:bg-green-500/20 transition-colors"
                >
                  <FlaskConical className="w-4 h-4" />
                  Run Benchmark
                </button>
              </>
            )}
            <div className="px-3 py-1 bg-claude-accent/10 border border-claude-accent/20 rounded-full">
              <span className="text-xs font-medium text-claude-accent">
                {currentDocument ? 'Document Loaded' : 'No Document'}
              </span>
            </div>
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
          Powered by Groq (Llama 3.3 70B) | Focusing on Middle Content Recovery
        </div>
      </footer>

      {/* Compare Strategies Modal */}
      {showCompareModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-claude-surface border border-claude-border rounded-xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-claude-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitCompare className="w-5 h-5 text-purple-400" />
                <h2 className="text-lg font-semibold text-claude-text">Compare All Strategies</h2>
              </div>
              <button onClick={() => setShowCompareModal(false)} className="p-1 hover:bg-claude-bg rounded">
                <X className="w-5 h-5 text-claude-text-secondary" />
              </button>
            </div>
            <div className="p-4 flex-1 overflow-y-auto">
              {!compareResults && !isComparing && (
                <div className="space-y-4">
                  <p className="text-sm text-claude-text-secondary">
                    Run the same question through all 6 strategies and compare results side-by-side.
                  </p>
                  <div>
                    <label className="block text-sm font-medium text-claude-text mb-2">Question to test:</label>
                    <textarea
                      value={compareQuestion}
                      onChange={(e) => setCompareQuestion(e.target.value)}
                      placeholder="Enter a question about your document..."
                      className="w-full p-3 bg-claude-bg border border-claude-border rounded-lg text-claude-text resize-none h-24"
                    />
                  </div>
                  <button
                    onClick={handleCompareStrategies}
                    disabled={!compareQuestion.trim()}
                    className="w-full py-2 bg-purple-500 hover:bg-purple-600 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
                  >
                    Compare All Strategies
                  </button>
                </div>
              )}
              {isComparing && (
                <div className="text-center py-12">
                  <div className="inline-block w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                  <p className="text-claude-text">Running all 6 strategies... This may take a minute.</p>
                </div>
              )}
              {compareResults && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-claude-text-secondary">
                      Best strategy: <span className="text-green-400 font-medium">{compareResults.bestStrategy}</span>
                    </p>
                    <button
                      onClick={() => { setCompareResults(null); setCompareQuestion(''); }}
                      className="text-sm text-claude-accent hover:underline"
                    >
                      Try another question
                    </button>
                  </div>
                  <div className="space-y-3">
                    {compareResults.comparison.map((result, idx) => (
                      <div
                        key={result.strategy}
                        className={`p-3 rounded-lg border ${idx === 0 ? 'border-green-500 bg-green-500/10' : 'border-claude-border bg-claude-bg'}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-claude-text">{result.strategy}</span>
                          <div className="flex items-center gap-2 text-xs">
                            <span className={`px-2 py-0.5 rounded ${result.confidence >= 0.8 ? 'bg-green-500/20 text-green-400' : result.confidence >= 0.5 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'}`}>
                              {Math.round(result.confidence * 100)}% confidence
                            </span>
                            <span className="text-claude-text-secondary">{result.latency.toFixed(1)}s</span>
                          </div>
                        </div>
                        <p className="text-sm text-claude-text-secondary line-clamp-3">{result.answer}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Benchmark Modal */}
      {showBenchmarkModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-claude-surface border border-claude-border rounded-xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-claude-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FlaskConical className="w-5 h-5 text-green-400" />
                <h2 className="text-lg font-semibold text-claude-text">Needle-in-Haystack Benchmark</h2>
              </div>
              <button onClick={() => setShowBenchmarkModal(false)} className="p-1 hover:bg-claude-bg rounded">
                <X className="w-5 h-5 text-claude-text-secondary" />
              </button>
            </div>
            <div className="p-4 flex-1 overflow-y-auto">
              {!benchmarkResults && !isBenchmarking && (
                <div className="space-y-4">
                  <p className="text-sm text-claude-text-secondary">
                    This test inserts a "needle" fact at different positions in your document and measures
                    how well baseline vs combined strategies find it. This maps the "attention dead zone."
                  </p>
                  <div className="bg-claude-bg p-3 rounded-lg border border-claude-border">
                    <p className="text-xs text-claude-text-secondary mb-2">Test positions:</p>
                    <div className="flex gap-2 flex-wrap">
                      {[10, 25, 40, 50, 60, 75, 90].map((pos) => (
                        <span key={pos} className={`px-2 py-1 rounded text-xs ${pos >= 33 && pos <= 66 ? 'bg-orange-500/20 text-orange-400' : 'bg-claude-surface text-claude-text-secondary'}`}>
                          {pos}%
                        </span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={handleRunBenchmark}
                    className="w-full py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
                  >
                    Run Benchmark (may take several minutes)
                  </button>
                </div>
              )}
              {isBenchmarking && (
                <div className="text-center py-12">
                  <div className="inline-block w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                  <p className="text-claude-text">Running needle-in-haystack tests at 7 positions...</p>
                  <p className="text-sm text-claude-text-secondary mt-2">This tests both baseline and combined strategies at each position.</p>
                </div>
              )}
              {benchmarkResults && (
                <div className="space-y-6">
                  {/* Summary Stats */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-red-400">{benchmarkResults.summary.baselineAccuracy}%</p>
                      <p className="text-xs text-claude-text-secondary">Baseline Accuracy</p>
                    </div>
                    <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-green-400">{benchmarkResults.summary.combinedAccuracy}%</p>
                      <p className="text-xs text-claude-text-secondary">Combined Accuracy</p>
                    </div>
                    <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-purple-400">+{benchmarkResults.summary.improvement}%</p>
                      <p className="text-xs text-claude-text-secondary">Improvement</p>
                    </div>
                  </div>

                  {/* Position Results */}
                  <div>
                    <h3 className="text-sm font-medium text-claude-text mb-3 flex items-center gap-2">
                      <BarChart3 className="w-4 h-4" />
                      Results by Position
                    </h3>
                    <div className="space-y-2">
                      {benchmarkResults.results.map((result) => (
                        <div
                          key={result.positionPercent}
                          className={`p-3 rounded-lg border ${result.positionZone === 'middle' ? 'border-orange-500/50 bg-orange-500/5' : 'border-claude-border bg-claude-bg'}`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <span className="font-mono text-sm text-claude-text">{result.positionPercent}%</span>
                              <span className={`text-xs px-2 py-0.5 rounded ${result.positionZone === 'middle' ? 'bg-orange-500/20 text-orange-400' : 'bg-claude-surface text-claude-text-secondary'}`}>
                                {result.positionZone}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-sm">
                              <span className={result.baselineFound ? 'text-green-400' : 'text-red-400'}>
                                Baseline: {result.baselineFound ? '✓' : '✗'}
                              </span>
                              <span className={result.combinedFound ? 'text-green-400' : 'text-red-400'}>
                                Combined: {result.combinedFound ? '✓' : '✗'}
                              </span>
                              {result.recoverySuccess && (
                                <span className="text-purple-400 text-xs">← Recovered!</span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {benchmarkResults.summary.deadZonePositions.length > 0 && (
                    <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3">
                      <p className="text-sm text-purple-400">
                        <strong>Dead zone recovery:</strong> Combined strategy recovered information at positions {benchmarkResults.summary.deadZonePositions.join('%, ')}% where baseline failed.
                      </p>
                    </div>
                  )}

                  <button
                    onClick={() => setBenchmarkResults(null)}
                    className="w-full py-2 bg-claude-bg border border-claude-border rounded-lg text-claude-text hover:bg-claude-surface transition-colors"
                  >
                    Run Another Benchmark
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
