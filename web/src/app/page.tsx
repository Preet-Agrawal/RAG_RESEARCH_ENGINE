'use client';

import { useState } from 'react';
import PDFUploader from '@/components/PDFUploader';
import ChatInterface from '@/components/ChatInterface';
import { FileText } from 'lucide-react';
import type { Message, PDFDocument } from '@/types';
import axios from 'axios';

export default function Home() {
  const [currentDocument, setCurrentDocument] = useState<PDFDocument | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

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

        // Add system message
        setMessages([
          {
            id: Date.now().toString(),
            role: 'assistant',
            content: `PDF "${file.name}" uploaded successfully! You can now ask questions about this document. I'll test the "Lost in the Middle" phenomenon by analyzing where information is retrieved from in the document.`,
            timestamp: new Date(),
          },
        ]);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Failed to upload PDF. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveDocument = () => {
    setCurrentDocument(null);
    setUploadedFilename('');
    setMessages([]);
  };

  const handleSendMessage = async (messageText: string) => {
    if (!uploadedFilename) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
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
      });

      if (response.data.success) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.data.answer,
          timestamp: new Date(),
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

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-claude-surface border-b border-claude-border px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-claude-accent/10 rounded-lg">
              <FileText className="w-6 h-6 text-claude-accent" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-claude-text">
                RAG Research Engine
              </h1>
              <p className="text-sm text-claude-text-secondary">
                Lost in the Middle Analysis
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
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
            <div className="h-full flex flex-col gap-4">
              {/* Document Info */}
              <div className="flex-shrink-0">
                <PDFUploader
                  onUpload={handleUpload}
                  currentDocument={currentDocument}
                  onRemove={handleRemoveDocument}
                />
              </div>

              {/* Chat */}
              <div className="flex-1 min-h-0 bg-claude-surface/30 border border-claude-border rounded-lg">
                <ChatInterface
                  messages={messages}
                  onSendMessage={handleSendMessage}
                  isLoading={isLoading}
                  disabled={!currentDocument}
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
                  <PDFUploader onUpload={handleUpload} />
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-claude-surface border-t border-claude-border px-6 py-3">
        <div className="max-w-7xl mx-auto text-center text-xs text-claude-text-secondary">
          Powered by Groq • Testing "Lost in the Middle" Phenomenon
        </div>
      </footer>
    </div>
  );
}
