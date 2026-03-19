'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, Plus } from 'lucide-react';
import type { PDFDocument } from '@/types';

interface PDFUploaderProps {
  onUpload: (file: File) => void;
  currentDocument?: PDFDocument | null;
  onRemove?: () => void;
  compact?: boolean;
}

export default function PDFUploader({ onUpload, currentDocument, onRemove, compact }: PDFUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0]);
    }
    setIsDragging(false);
  }, [onUpload]);

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    onDragEnter: () => setIsDragging(true),
    onDragLeave: () => setIsDragging(false),
  });

  if (currentDocument) {
    return (
      <div className="flex items-center justify-between p-3 bg-claude-surface border border-claude-border rounded-xl">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-1.5 bg-claude-accent-soft rounded-lg flex-shrink-0">
            <File className="w-4 h-4 text-claude-accent" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-claude-text truncate">{currentDocument.name}</p>
            <p className="text-xs text-claude-text-muted">
              {(currentDocument.size / 1024).toFixed(1)} KB
            </p>
          </div>
        </div>
        {onRemove && (
          <button
            onClick={onRemove}
            className="p-1.5 rounded-lg hover:bg-claude-surface-hover text-claude-text-muted hover:text-red-400 transition-colors flex-shrink-0"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    );
  }

  // Compact mode for sidebar
  if (compact) {
    return (
      <div
        {...getRootProps()}
        className={`
          flex items-center gap-2.5 p-3 rounded-xl cursor-pointer transition-all duration-150
          border border-dashed
          ${isDragging
            ? 'border-claude-accent bg-claude-accent-soft'
            : 'border-claude-border hover:border-claude-accent/40 hover:bg-claude-surface'
          }
        `}
      >
        <input {...getInputProps()} />
        <div className={`p-1.5 rounded-lg ${isDragging ? 'bg-claude-accent/20' : 'bg-claude-surface'}`}>
          <Plus className={`w-4 h-4 ${isDragging ? 'text-claude-accent' : 'text-claude-text-muted'}`} />
        </div>
        <span className={`text-sm ${isDragging ? 'text-claude-accent' : 'text-claude-text-secondary'}`}>
          {isDragging ? 'Drop PDF' : 'Upload PDF'}
        </span>
      </div>
    );
  }

  // Full mode for landing page
  return (
    <div
      {...getRootProps()}
      className={`
        group relative rounded-2xl cursor-pointer transition-all duration-300 overflow-hidden
        ${isDragging
          ? 'ring-2 ring-claude-accent ring-offset-2 ring-offset-claude-bg'
          : 'hover:ring-1 hover:ring-claude-border-light'
        }
      `}
    >
      <input {...getInputProps()} />
      {/* Gradient border effect */}
      <div className={`absolute inset-0 rounded-2xl bg-gradient-to-b from-claude-border-light/50 via-claude-border/30 to-claude-border-light/50 p-px transition-opacity ${isDragging ? 'opacity-0' : 'opacity-100'}`}>
        <div className="w-full h-full rounded-2xl bg-claude-bg" />
      </div>

      <div className={`relative p-8 text-center transition-colors ${isDragging ? 'bg-claude-accent/5' : ''}`}>
        <div className="flex flex-col items-center gap-4">
          <div className={`
            w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300
            ${isDragging
              ? 'bg-claude-accent/15 scale-110'
              : 'bg-claude-surface border border-claude-border group-hover:border-claude-border-light group-hover:scale-105'
            }
          `}>
            <Upload className={`w-6 h-6 transition-colors ${isDragging ? 'text-claude-accent' : 'text-claude-text-muted group-hover:text-claude-text-secondary'}`} />
          </div>
          <div>
            <p className="text-base font-semibold text-claude-text mb-1.5">
              {isDragging ? 'Drop your PDF here' : 'Upload a PDF document'}
            </p>
            <p className="text-sm text-claude-text-muted">
              Drag and drop or <span className="text-claude-accent">browse files</span>
            </p>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-claude-text-muted">
            <span className="flex items-center gap-1">
              <File className="w-3 h-3" />
              PDF only
            </span>
            <span className="w-px h-3 bg-claude-border" />
            <span>Max 50MB</span>
          </div>
        </div>
      </div>
    </div>
  );
}
