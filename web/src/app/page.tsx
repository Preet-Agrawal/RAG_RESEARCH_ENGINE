'use client';

import { useState } from 'react';
import PDFUploader from '@/components/PDFUploader';
import ChatInterface from '@/components/ChatInterface';
import {
  Beaker, FileText, ChevronDown, ChevronUp, GitCompare, FlaskConical,
  X, BarChart3, PanelLeftClose, PanelLeft, Plus, Trash2
} from 'lucide-react';
import type {
  Message, PDFDocument, Strategy, RAGResponse, ChunkSummary,
  SummarizeResponse, CompareResponse, BenchmarkResponse
} from '@/types';
import axios from 'axios';

interface SummaryData {
  chunkSummaries: ChunkSummary[];
  overallSummary: string;
  latency?: number;
}

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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setMessages([]);
    setSummaryData(null);
    setChunkSummaries([]);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Set document early so we switch to chat view and show loading there
      setCurrentDocument({
        file,
        name: file.name,
        size: file.size,
        uploadedAt: new Date(),
      });

      const response = await axios.post('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.data.success) {
        setUploadedFilename(response.data.filename);
        setIsUploading(false);
        setIsSummarizing(true);

        try {
          const summarizeResponse = await axios.post<SummarizeResponse>('/api/summarize', {
            filename: response.data.filename,
          });

          if (summarizeResponse.data.success) {
            setChunkSummaries(summarizeResponse.data.chunkSummaries);
            const totalCount = summarizeResponse.data.totalChunks;

            setSummaryData({
              chunkSummaries: summarizeResponse.data.chunkSummaries,
              overallSummary: summarizeResponse.data.overallSummary,
              latency: summarizeResponse.data.latency,
            });

            setMessages([
              {
                id: 'summary-' + Date.now().toString(),
                role: 'assistant',
                content: `__SUMMARY__`,
                timestamp: new Date(),
                metadata: {
                  latency: summarizeResponse.data.latency,
                  chunksProcessed: totalCount,
                },
              },
            ]);
          }
        } catch (error: any) {
          console.error('Summarize failed:', error);
          const errMsg = error?.response?.data?.error || error?.message || 'Unknown error';
          setMessages([
            {
              id: Date.now().toString(),
              role: 'assistant',
              content: `Could not analyze the document: ${errMsg}`,
              timestamp: new Date(),
            },
          ]);
        } finally {
          setIsSummarizing(false);
        }
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setCurrentDocument(null);
      alert('Failed to upload PDF. Please try again.');
      setIsUploading(false);
    }
  };

  const handleRemoveDocument = () => {
    setCurrentDocument(null);
    setUploadedFilename('');
    setMessages([]);
    setChunkSummaries([]);
    setSummaryData(null);
  };

  const handleNewChat = () => {
    setCurrentDocument(null);
    setUploadedFilename('');
    setMessages([]);
    setChunkSummaries([]);
    setSummaryData(null);
    setCompareResults(null);
    setBenchmarkResults(null);
    setShowCompareModal(false);
    setShowBenchmarkModal(false);
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
    if (isMiddle) return 'border-l-orange-500 bg-orange-500/5';
    if (zone === 'beginning') return 'border-l-emerald-500 bg-emerald-500/5';
    return 'border-l-blue-500 bg-blue-500/5';
  };

  const getZoneLabel = (zone: string) => {
    if (zone === 'middle') return 'Middle';
    if (zone === 'beginning') return 'Start';
    return 'End';
  };

  return (
    <div className="h-screen flex overflow-hidden bg-claude-bg">
      {/* Sidebar */}
      <aside
        className={`sidebar-transition flex flex-col bg-claude-sidebar border-r border-claude-border ${
          sidebarOpen ? 'w-72' : 'w-0'
        } overflow-hidden flex-shrink-0`}
      >
        <div className="flex flex-col h-full min-w-[18rem]">
          {/* Sidebar Header */}
          <div className="p-3 flex items-center justify-between">
            <button
              onClick={handleNewChat}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-claude-surface-hover text-claude-text-secondary hover:text-claude-text transition-colors text-sm flex-1"
            >
              <Plus className="w-4 h-4" />
              New Chat
            </button>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-2 rounded-lg hover:bg-claude-surface-hover text-claude-text-secondary hover:text-claude-text transition-colors"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* Document Section */}
          <div className="px-3 mb-2">
            {currentDocument ? (
              <div className="p-3 bg-claude-surface rounded-xl border border-claude-border">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="p-1.5 bg-claude-accent-soft rounded-lg flex-shrink-0">
                      <FileText className="w-4 h-4 text-claude-accent" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-claude-text truncate">
                        {currentDocument.name}
                      </p>
                      <p className="text-xs text-claude-text-muted">
                        {(currentDocument.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleRemoveDocument}
                    className="p-1 rounded hover:bg-claude-surface-hover text-claude-text-muted hover:text-red-400 transition-colors flex-shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ) : (
              <PDFUploader onUpload={handleUpload} compact />
            )}
          </div>

          {/* Action Buttons */}
          {currentDocument && (
            <div className="px-3 space-y-1 mb-3">
              <button
                onClick={() => setShowCompareModal(true)}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-claude-surface-hover text-claude-text-secondary hover:text-claude-text transition-colors text-sm"
              >
                <GitCompare className="w-4 h-4 text-purple-400" />
                Compare Strategies
              </button>
              <button
                onClick={() => setShowBenchmarkModal(true)}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-claude-surface-hover text-claude-text-secondary hover:text-claude-text transition-colors text-sm"
              >
                <FlaskConical className="w-4 h-4 text-emerald-400" />
                Run Benchmark
              </button>
            </div>
          )}

          {/* Chunk Summaries */}
          {chunkSummaries.length > 0 && (
            <div className="flex-1 flex flex-col overflow-hidden border-t border-claude-border">
              <div className="px-3 py-2.5 flex items-center justify-between">
                <h3 className="text-xs font-semibold text-claude-text-muted uppercase tracking-wider">
                  Document Sections
                </h3>
                <button
                  onClick={() => setShowAllChunks(!showAllChunks)}
                  className="text-xs text-claude-accent hover:text-claude-accent-hover flex items-center gap-0.5 transition-colors"
                >
                  {showAllChunks ? 'Less' : 'All'}
                  {showAllChunks ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
              </div>
              <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
                {(showAllChunks
                  ? chunkSummaries
                  : chunkSummaries.filter(c => c.isMiddle || c.chunkId <= 2 || c.chunkId >= chunkSummaries.length - 1)
                ).map((chunk) => (
                  <div
                    key={chunk.chunkId}
                    className={`p-2.5 rounded-lg border-l-2 ${getZoneColor(chunk.zone, chunk.isMiddle)}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-claude-text-secondary">
                        {chunk.chunkId}/{chunk.totalChunks}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                        chunk.isMiddle
                          ? 'bg-orange-500/15 text-orange-400'
                          : 'bg-claude-surface text-claude-text-muted'
                      }`}>
                        {getZoneLabel(chunk.zone)}
                      </span>
                    </div>
                    <p className="text-xs text-claude-text-secondary leading-relaxed line-clamp-2">
                      {chunk.summary}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sidebar Footer */}
          <div className="p-3 border-t border-claude-border">
            <div className="flex items-center gap-2 px-2">
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-claude-accent to-amber-600 flex items-center justify-center">
                <Beaker className="w-3.5 h-3.5 text-white" />
              </div>
              <div>
                <p className="text-xs font-medium text-claude-text">RAG Research Engine</p>
                <p className="text-[10px] text-claude-text-muted">Groq Llama 3.3 70B</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <div className="h-12 flex items-center px-4 border-b border-claude-border bg-claude-surface/50 flex-shrink-0">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-claude-surface-hover text-claude-text-secondary hover:text-claude-text transition-colors mr-2"
            >
              <PanelLeft className="w-4 h-4" />
            </button>
          )}
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-medium text-claude-text">
              {currentDocument ? currentDocument.name : 'RAG Research Engine'}
            </h1>
            {currentDocument && (
              <span className="text-xs text-claude-text-muted">
                &middot; Lost in the Middle Recovery
              </span>
            )}
          </div>
        </div>

        {/* Chat Content */}
        {currentDocument ? (
          <ChatInterface
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            isProcessing={isUploading || isSummarizing}
            processingLabel={isUploading ? 'Uploading PDF...' : isSummarizing ? 'Analyzing document sections...' : ''}
            disabled={!currentDocument || isSummarizing || isUploading}
            selectedStrategy={selectedStrategy}
            onStrategyChange={handleStrategyChange}
            summaryData={summaryData}
            documentName={currentDocument?.name || ''}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="max-w-xl w-full space-y-8">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-claude-accent/20 to-amber-600/20 mb-5">
                  <Beaker className="w-7 h-7 text-claude-accent" />
                </div>
                <h2 className="text-2xl font-semibold text-claude-text mb-2">
                  RAG Research Engine
                </h2>
                <p className="text-claude-text-secondary text-sm max-w-md mx-auto leading-relaxed">
                  Upload a PDF to explore the Lost in the Middle phenomenon.
                  Ask questions and compare recovery strategies.
                </p>
              </div>
              <PDFUploader onUpload={handleUpload} />
              <div className="grid grid-cols-2 gap-3">
                {[
                  { title: 'Smart Chunking', desc: 'Position-aware document splitting' },
                  { title: 'Middle Recovery', desc: 'Strategies to recover lost content' },
                  { title: 'Strategy Comparison', desc: 'Compare 7 recovery approaches' },
                  { title: 'Needle Benchmark', desc: 'Map attention dead zones' },
                ].map((item) => (
                  <div
                    key={item.title}
                    className="p-3.5 rounded-xl bg-claude-surface border border-claude-border hover:border-claude-border-light transition-colors"
                  >
                    <p className="text-sm font-medium text-claude-text mb-0.5">{item.title}</p>
                    <p className="text-xs text-claude-text-muted">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>


      {/* Compare Strategies Modal */}
      {showCompareModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-claude-surface border border-claude-border rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col shadow-2xl">
            <div className="px-5 py-4 border-b border-claude-border flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <GitCompare className="w-5 h-5 text-purple-400" />
                <h2 className="text-base font-semibold text-claude-text">Compare All Strategies</h2>
              </div>
              <button
                onClick={() => setShowCompareModal(false)}
                className="p-1.5 hover:bg-claude-surface-hover rounded-lg transition-colors"
              >
                <X className="w-4 h-4 text-claude-text-muted" />
              </button>
            </div>
            <div className="p-5 flex-1 overflow-y-auto">
              {!compareResults && !isComparing && (
                <div className="space-y-4">
                  <p className="text-sm text-claude-text-secondary">
                    Run the same question through all strategies and compare results.
                  </p>
                  <div>
                    <label className="block text-sm font-medium text-claude-text mb-2">Question</label>
                    <textarea
                      value={compareQuestion}
                      onChange={(e) => setCompareQuestion(e.target.value)}
                      placeholder="Enter a question about your document..."
                      className="w-full p-3 bg-claude-bg border border-claude-border rounded-xl text-claude-text text-sm resize-none h-24 focus:outline-none focus:border-claude-accent/50 placeholder-claude-text-muted"
                    />
                  </div>
                  <button
                    onClick={handleCompareStrategies}
                    disabled={!compareQuestion.trim()}
                    className="w-full py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-40 text-white rounded-xl text-sm font-medium transition-colors"
                  >
                    Compare All Strategies
                  </button>
                </div>
              )}
              {isComparing && (
                <div className="text-center py-16">
                  <div className="flex justify-center gap-1.5 mb-4">
                    <div className="typing-dot" style={{ background: '#a855f7' }} />
                    <div className="typing-dot" style={{ background: '#a855f7', animationDelay: '-0.16s' }} />
                    <div className="typing-dot" style={{ background: '#a855f7', animationDelay: '0s' }} />
                  </div>
                  <p className="text-sm text-claude-text-secondary">Running all strategies...</p>
                </div>
              )}
              {compareResults && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-claude-text-secondary">
                      Best: <span className="text-emerald-400 font-medium">{compareResults.bestStrategy}</span>
                    </p>
                    <button
                      onClick={() => { setCompareResults(null); setCompareQuestion(''); }}
                      className="text-xs text-claude-accent hover:text-claude-accent-hover transition-colors"
                    >
                      Try another
                    </button>
                  </div>
                  <div className="space-y-2">
                    {compareResults.comparison.map((result, idx) => (
                      <div
                        key={result.strategy}
                        className={`p-3.5 rounded-xl border ${
                          idx === 0
                            ? 'border-emerald-500/40 bg-emerald-500/5'
                            : 'border-claude-border bg-claude-bg'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-claude-text">
                            {idx === 0 && <span className="text-emerald-400 mr-1.5">&#9679;</span>}
                            {result.strategy}
                          </span>
                          <div className="flex items-center gap-2 text-xs">
                            <span className={`px-2 py-0.5 rounded-full ${
                              result.confidence >= 0.8 ? 'bg-emerald-500/15 text-emerald-400' :
                              result.confidence >= 0.5 ? 'bg-yellow-500/15 text-yellow-400' :
                              'bg-red-500/15 text-red-400'
                            }`}>
                              {Math.round(result.confidence * 100)}%
                            </span>
                            <span className="text-claude-text-muted">{result.latency.toFixed(1)}s</span>
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-claude-surface border border-claude-border rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col shadow-2xl">
            <div className="px-5 py-4 border-b border-claude-border flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <FlaskConical className="w-5 h-5 text-emerald-400" />
                <h2 className="text-base font-semibold text-claude-text">Needle-in-Haystack Benchmark</h2>
              </div>
              <button
                onClick={() => setShowBenchmarkModal(false)}
                className="p-1.5 hover:bg-claude-surface-hover rounded-lg transition-colors"
              >
                <X className="w-4 h-4 text-claude-text-muted" />
              </button>
            </div>
            <div className="p-5 flex-1 overflow-y-auto">
              {!benchmarkResults && !isBenchmarking && (
                <div className="space-y-4">
                  <p className="text-sm text-claude-text-secondary">
                    Insert a "needle" fact at different positions and measure how well strategies find it.
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    {[10, 25, 40, 50, 60, 75, 90].map((pos) => (
                      <span
                        key={pos}
                        className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                          pos >= 33 && pos <= 66
                            ? 'bg-orange-500/15 text-orange-400'
                            : 'bg-claude-bg text-claude-text-muted'
                        }`}
                      >
                        {pos}%
                      </span>
                    ))}
                  </div>
                  <button
                    onClick={handleRunBenchmark}
                    className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-medium transition-colors"
                  >
                    Run Benchmark
                  </button>
                </div>
              )}
              {isBenchmarking && (
                <div className="text-center py-16">
                  <div className="flex justify-center gap-1.5 mb-4">
                    <div className="typing-dot" style={{ background: '#10b981' }} />
                    <div className="typing-dot" style={{ background: '#10b981', animationDelay: '-0.16s' }} />
                    <div className="typing-dot" style={{ background: '#10b981', animationDelay: '0s' }} />
                  </div>
                  <p className="text-sm text-claude-text-secondary">Testing at 7 positions...</p>
                </div>
              )}
              {benchmarkResults && (
                <div className="space-y-5">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-red-500/8 border border-red-500/20 rounded-xl p-3.5 text-center">
                      <p className="text-2xl font-bold text-red-400">{benchmarkResults.summary.baselineAccuracy}%</p>
                      <p className="text-xs text-claude-text-muted mt-0.5">Baseline</p>
                    </div>
                    <div className="bg-emerald-500/8 border border-emerald-500/20 rounded-xl p-3.5 text-center">
                      <p className="text-2xl font-bold text-emerald-400">{benchmarkResults.summary.combinedAccuracy}%</p>
                      <p className="text-xs text-claude-text-muted mt-0.5">Combined</p>
                    </div>
                    <div className="bg-purple-500/8 border border-purple-500/20 rounded-xl p-3.5 text-center">
                      <p className="text-2xl font-bold text-purple-400">+{benchmarkResults.summary.improvement}%</p>
                      <p className="text-xs text-claude-text-muted mt-0.5">Improvement</p>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-xs font-semibold text-claude-text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
                      <BarChart3 className="w-3.5 h-3.5" />
                      Results by Position
                    </h3>
                    <div className="space-y-1.5">
                      {benchmarkResults.results.map((result) => (
                        <div
                          key={result.positionPercent}
                          className={`p-3 rounded-xl flex items-center justify-between ${
                            result.positionZone === 'middle'
                              ? 'bg-orange-500/5 border border-orange-500/20'
                              : 'bg-claude-bg border border-claude-border'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <span className="font-mono text-sm text-claude-text w-8">{result.positionPercent}%</span>
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                              result.positionZone === 'middle'
                                ? 'bg-orange-500/15 text-orange-400'
                                : 'bg-claude-surface text-claude-text-muted'
                            }`}>
                              {result.positionZone}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-sm">
                            <span className={result.baselineFound ? 'text-emerald-400' : 'text-red-400'}>
                              Baseline {result.baselineFound ? '✓' : '✗'}
                            </span>
                            <span className={result.combinedFound ? 'text-emerald-400' : 'text-red-400'}>
                              Combined {result.combinedFound ? '✓' : '✗'}
                            </span>
                            {result.recoverySuccess && (
                              <span className="text-purple-400 text-xs font-medium">Recovered</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {benchmarkResults.summary.deadZonePositions.length > 0 && (
                    <div className="bg-purple-500/8 border border-purple-500/20 rounded-xl p-3.5">
                      <p className="text-sm text-purple-400">
                        Dead zone recovery at: {benchmarkResults.summary.deadZonePositions.join('%, ')}%
                      </p>
                    </div>
                  )}

                  <button
                    onClick={() => setBenchmarkResults(null)}
                    className="w-full py-2.5 bg-claude-bg border border-claude-border rounded-xl text-sm text-claude-text hover:bg-claude-surface-hover transition-colors"
                  >
                    Run Again
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
