import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import ChatUI from './components/ChatUI.jsx';
import Dashboard from './components/Dashboard.jsx';
import { CompareResultsTable, BenchmarkResultsTable } from './components/Dashboard.jsx';

const CHATS_KEY = 'rag_saved_chats';

function loadChats() {
  try {
    return JSON.parse(localStorage.getItem(CHATS_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveChats(chats) {
  try {
    localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
  } catch {
    /* ignore */
  }
}

function ThemeToggle() {
  const [theme, setTheme] = useState(null);

  useEffect(() => {
    setTheme(document.documentElement.classList.contains('dark') ? 'dark' : 'light');
  }, []);

  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.classList.toggle('dark', next === 'dark');
    try {
      localStorage.setItem('theme', next);
    } catch {
      /* ignore */
    }
  };

  if (theme === null) return null;

  return (
    <button type="button" className="sidebar-btn" onClick={toggle}>
      {theme === 'dark' ? '☀ Light Mode' : '🌙 Dark Mode'}
    </button>
  );
}

function PDFUploader({ onUpload, compact }) {
  const [dragging, setDragging] = useState(false);
  const inputId = compact ? 'pdf-upload-compact' : 'pdf-upload-full';

  const handleFile = (file) => {
    if (file && file.name.toLowerCase().endsWith('.pdf')) {
      onUpload(file);
    }
  };

  return (
    <label
      htmlFor={inputId}
      className={`upload-zone ${compact ? 'upload-compact' : 'upload-full'} ${dragging ? 'upload-dragging' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
      }}
    >
      <input
        id={inputId}
        type="file"
        accept="application/pdf"
        className="sr-only"
        onChange={(e) => {
          if (e.target.files[0]) handleFile(e.target.files[0]);
        }}
      />
      {compact ? (
        <span>{dragging ? 'Drop PDF' : '+ Upload PDF'}</span>
      ) : (
        <div className="upload-inner">
          <p className="upload-title">
            {dragging ? 'Drop your PDF here' : 'Upload a PDF document'}
          </p>
          <p className="upload-sub">Drag and drop or browse — PDF only</p>
        </div>
      )}
    </label>
  );
}

export default function App() {
  const [currentDocument, setCurrentDocument] = useState(null);
  const [uploadedFilename, setUploadedFilename] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState('combined');
  const [summaryData, setSummaryData] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [toast, setToast] = useState(null);
  const [view, setView] = useState('chat');

  const [showCompareModal, setShowCompareModal] = useState(false);
  const [showBenchmarkModal, setShowBenchmarkModal] = useState(false);
  const [compareQuestion, setCompareQuestion] = useState('');
  const [compareResults, setCompareResults] = useState(null);
  const [benchmarkResults, setBenchmarkResults] = useState(null);
  const [isComparing, setIsComparing] = useState(false);
  const [isBenchmarking, setIsBenchmarking] = useState(false);

  const [savedChats, setSavedChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);

  useEffect(() => {
    setSavedChats(loadChats());
  }, []);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const saveCurrentChat = useCallback(() => {
    if (!activeChatId || messages.length === 0 || !uploadedFilename) return;
    const firstUser = messages.find((m) => m.role === 'user');
    const chats = loadChats().filter((c) => c.id !== activeChatId);
    chats.unshift({
      id: activeChatId,
      title: firstUser?.content?.slice(0, 60) || currentDocument?.name || 'New Chat',
      documentName: currentDocument?.name || '',
      uploadedFilename,
      messages: messages.map((m) => ({
        ...m,
        timestamp: m.timestamp.toISOString(),
      })),
      updatedAt: new Date().toISOString(),
    });
    saveChats(chats.slice(0, 50));
    setSavedChats(chats.slice(0, 50));
  }, [activeChatId, messages, uploadedFilename, currentDocument]);

  useEffect(() => {
    if (messages.length > 0 && activeChatId) {
      const t = setTimeout(saveCurrentChat, 500);
      return () => clearTimeout(t);
    }
  }, [messages, saveCurrentChat, activeChatId]);

  const handleUpload = async (file) => {
    setIsUploading(true);
    setMessages([]);
    setSummaryData(null);
    const newChatId = `chat-${Date.now()}`;
    setActiveChatId(newChatId);

    try {
      setCurrentDocument({
        name: file.name,
        size: file.size,
        uploadedAt: new Date(),
      });

      const formData = new FormData();
      formData.append('file', file);
      const response = await axios.post('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.data.success) {
        setUploadedFilename(response.data.filename);
        setIsUploading(false);
        setIsSummarizing(true);

        try {
          const summarizeResponse = await axios.post('/api/summarize', {
            filename: response.data.filename,
          });

          if (summarizeResponse.data.success) {
            setSummaryData({
              chunkSummaries: summarizeResponse.data.chunkSummaries,
              overallSummary: summarizeResponse.data.overallSummary,
              latency: summarizeResponse.data.latency,
            });
            setMessages([
              {
                id: `summary-${Date.now()}`,
                role: 'assistant',
                content: '__SUMMARY__',
                timestamp: new Date(),
                metadata: {
                  latency: summarizeResponse.data.latency,
                  chunksProcessed: summarizeResponse.data.totalChunks,
                },
              },
            ]);
          }
        } catch (error) {
          const errMsg =
            error.response?.data?.error || error.message || 'Unknown error';
          setMessages([
            {
              id: String(Date.now()),
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
      const errMsg = error.response?.data?.error || error.message || 'Unknown error';
      setCurrentDocument(null);
      showToast(`Failed to upload PDF: ${errMsg}`, 'error');
      setIsUploading(false);
    }
  };

  const handleNewChat = () => {
    saveCurrentChat();
    setCurrentDocument(null);
    setUploadedFilename('');
    setMessages([]);
    setSummaryData(null);
    setCompareResults(null);
    setBenchmarkResults(null);
    setActiveChatId(null);
    setView('chat');
  };

  const handleRestoreChat = (chatId) => {
    const chat = loadChats().find((c) => c.id === chatId);
    if (!chat) return;
    setActiveChatId(chatId);
    setMessages(
      chat.messages.map((m) => ({
        ...m,
        timestamp: new Date(m.timestamp),
      }))
    );
    setUploadedFilename(chat.uploadedFilename);
    setCurrentDocument({
      name: chat.documentName,
      size: 0,
      uploadedAt: new Date(),
    });
    setSummaryData(null);
    setView('chat');
  };

  const handleDeleteChat = (chatId) => {
    const chats = loadChats().filter((c) => c.id !== chatId);
    saveChats(chats);
    setSavedChats(chats);
    if (activeChatId === chatId) handleNewChat();
  };

  const handleSendMessage = async (messageText) => {
    if (!uploadedFilename) return;

    const userMessage = {
      id: String(Date.now()),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await axios.post('/api/ask', {
        question: messageText,
        filename: uploadedFilename,
        strategy: selectedStrategy,
      });

      if (response.data.success) {
        setMessages((prev) => [
          ...prev,
          {
            id: String(Date.now() + 1),
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
          },
        ]);
      } else {
        throw new Error(response.data.error || 'Unknown error');
      }
    } catch (error) {
      const errText =
        error.response?.data?.error || error.message || 'Request failed';
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          role: 'assistant',
          content: `Sorry, I encountered an error: ${errText}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompareStrategies = async () => {
    if (!uploadedFilename || !compareQuestion.trim()) return;
    setIsComparing(true);
    setCompareResults(null);
    try {
      const response = await axios.post('/api/compare', {
        question: compareQuestion,
        filename: uploadedFilename,
      });
      if (response.data.success) {
        setCompareResults(response.data);
        setView('dashboard');
      }
    } catch (error) {
      showToast(
        `Failed to compare: ${error.response?.data?.error || error.message}`,
        'error'
      );
    } finally {
      setIsComparing(false);
    }
  };

  const handleRunBenchmark = async () => {
    if (!uploadedFilename) return;
    setIsBenchmarking(true);
    setBenchmarkResults(null);
    try {
      const response = await axios.post('/api/benchmark', {
        filename: uploadedFilename,
      });
      if (response.data.success) {
        setBenchmarkResults(response.data);
        setView('dashboard');
      }
    } catch (error) {
      showToast(
        `Failed to run benchmark: ${error.response?.data?.error || error.message}`,
        'error'
      );
    } finally {
      setIsBenchmarking(false);
    }
  };

  const featureCards = [
    {
      title: 'Smart Chunking',
      desc: 'Position-aware document splitting with overlap detection',
    },
    {
      title: 'Middle Recovery',
      desc: '11 strategies to recover content LLMs typically miss',
    },
    {
      title: 'Strategy Comparison',
      desc: 'Run queries across all strategies and compare results',
    },
    {
      title: 'Needle Benchmark',
      desc: 'Test retrieval accuracy at every document position',
    },
  ];

  return (
    <div className="app-shell">
      {toast && (
        <div className={`toast toast-${toast.type}`} role="status">
          {toast.message}
        </div>
      )}

      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <div className="sidebar-inner">
          <div className="sidebar-header">
            <button type="button" className="sidebar-btn" onClick={handleNewChat}>
              + New Chat
            </button>
            <button
              type="button"
              className="sidebar-icon-btn"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close sidebar"
            >
              ‹
            </button>
          </div>

          <div className="sidebar-section">
            {currentDocument ? (
              <div className="doc-card">
                <p className="doc-name">{currentDocument.name}</p>
                <p className="doc-meta">
                  {currentDocument.size > 0
                    ? `${(currentDocument.size / 1024).toFixed(1)} KB`
                    : 'Restored'}
                </p>
                <button
                  type="button"
                  className="link-danger"
                  onClick={() => {
                    setCurrentDocument(null);
                    setUploadedFilename('');
                    setMessages([]);
                    setSummaryData(null);
                  }}
                >
                  Remove
                </button>
              </div>
            ) : (
              <PDFUploader onUpload={handleUpload} compact />
            )}
          </div>

          {currentDocument && (
            <div className="sidebar-actions">
              <button
                type="button"
                className="sidebar-btn"
                onClick={() => setShowCompareModal(true)}
              >
                Compare Strategies
              </button>
              <button
                type="button"
                className="sidebar-btn"
                onClick={() => setShowBenchmarkModal(true)}
              >
                Run Benchmark
              </button>
              <button
                type="button"
                className={`sidebar-btn ${view === 'dashboard' ? 'active' : ''}`}
                onClick={() => setView('dashboard')}
              >
                Results Dashboard
              </button>
            </div>
          )}

          <div className="chat-history">
            <p className="history-label">Recent chats</p>
            {savedChats.length === 0 && (
              <p className="history-empty">No saved chats yet</p>
            )}
            {savedChats.map((chat) => (
              <div
                key={chat.id}
                className={`history-item ${activeChatId === chat.id ? 'active' : ''}`}
              >
                <button
                  type="button"
                  className="history-title"
                  onClick={() => handleRestoreChat(chat.id)}
                >
                  {chat.title}
                </button>
                <button
                  type="button"
                  className="history-delete"
                  onClick={() => handleDeleteChat(chat.id)}
                  aria-label="Delete chat"
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          <div className="sidebar-footer">
            <ThemeToggle />
            <p className="brand">RAG Research Engine</p>
            <p className="brand-sub">Groq + Gemini auto-fallback</p>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          {!sidebarOpen && (
            <button
              type="button"
              className="sidebar-icon-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              ›
            </button>
          )}
          <h1 className="topbar-title">
            {currentDocument ? currentDocument.name : 'RAG Research Engine'}
          </h1>
          <div className="topbar-actions">
            {currentDocument && (
              <>
                <button
                  type="button"
                  className={`tab-btn ${view === 'chat' ? 'active' : ''}`}
                  onClick={() => setView('chat')}
                >
                  Chat
                </button>
                <button
                  type="button"
                  className={`tab-btn ${view === 'dashboard' ? 'active' : ''}`}
                  onClick={() => setView('dashboard')}
                >
                  Dashboard
                </button>
              </>
            )}
            <button type="button" className="sidebar-btn" onClick={handleNewChat}>
              New Chat
            </button>
          </div>
        </header>

        {currentDocument ? (
          view === 'chat' ? (
            <ChatUI
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              isProcessing={isUploading || isSummarizing}
              processingLabel={
                isUploading
                  ? 'Uploading PDF...'
                  : isSummarizing
                    ? 'Analyzing document sections...'
                    : ''
              }
              disabled={!currentDocument || isSummarizing || isUploading}
              selectedStrategy={selectedStrategy}
              onStrategyChange={setSelectedStrategy}
              summaryData={summaryData}
              documentName={currentDocument.name}
            />
          ) : (
            <div className="dashboard-view">
              <Dashboard
                compareResults={compareResults}
                benchmarkResults={benchmarkResults}
              />
            </div>
          )
        ) : (
          <div className="landing">
            <div className="landing-inner">
              <h1 className="landing-title">RAG Research Engine</h1>
              <p className="landing-desc">
                Explore the Lost in the Middle phenomenon. Upload a document, pick
                from 11 recovery strategies, and compare results.
              </p>
              <PDFUploader onUpload={handleUpload} />
              <div className="feature-grid">
                {featureCards.map((card) => (
                  <div key={card.title} className="feature-card">
                    <p className="feature-title">{card.title}</p>
                    <p className="feature-desc">{card.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {showCompareModal && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal">
            <div className="modal-header">
              <h2>Compare All Strategies</h2>
              <button
                type="button"
                className="modal-close"
                onClick={() => setShowCompareModal(false)}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              {!compareResults && !isComparing && (
                <>
                  <textarea
                    className="modal-textarea"
                    value={compareQuestion}
                    onChange={(e) => setCompareQuestion(e.target.value)}
                    placeholder="Enter a question about your document..."
                    rows={4}
                  />
                  <button
                    type="button"
                    className="btn btn-purple"
                    disabled={!compareQuestion.trim()}
                    onClick={handleCompareStrategies}
                  >
                    Compare All Strategies
                  </button>
                </>
              )}
              {isComparing && (
                <p className="modal-loading">Running all strategies...</p>
              )}
              {compareResults && (
                <>
                  <CompareResultsTable
                    results={compareResults.comparison}
                    bestStrategy={compareResults.bestStrategy}
                  />
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setCompareResults(null);
                      setCompareQuestion('');
                    }}
                  >
                    Try another
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {showBenchmarkModal && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal">
            <div className="modal-header">
              <h2>Needle-in-Haystack Benchmark</h2>
              <button
                type="button"
                className="modal-close"
                onClick={() => setShowBenchmarkModal(false)}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              {!benchmarkResults && !isBenchmarking && (
                <>
                  <p className="modal-hint">
                    Inserts a needle fact at 7 positions and measures retrieval.
                  </p>
                  <button
                    type="button"
                    className="btn btn-success"
                    onClick={handleRunBenchmark}
                  >
                    Run Benchmark
                  </button>
                </>
              )}
              {isBenchmarking && (
                <p className="modal-loading">Testing at 7 positions...</p>
              )}
              {benchmarkResults && (
                <>
                  <BenchmarkResultsTable benchmark={benchmarkResults} />
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setBenchmarkResults(null)}
                  >
                    Run Again
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
