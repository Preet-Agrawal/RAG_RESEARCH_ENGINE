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
        border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
        transition-all duration-200
        ${isDragging
          ? 'border-claude-accent bg-claude-accent-soft'
          : 'border-claude-border hover:border-claude-text-muted/40 hover:bg-claude-surface/30'
        }
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        <div className={`
          p-3.5 rounded-2xl transition-colors
          ${isDragging ? 'bg-claude-accent/20' : 'bg-claude-surface'}
        `}>
          <Upload className={`w-7 h-7 ${isDragging ? 'text-claude-accent' : 'text-claude-text-muted'}`} />
        </div>
        <div>
          <p className="text-base font-medium text-claude-text mb-1">
            {isDragging ? 'Drop your PDF here' : 'Upload PDF Document'}
          </p>
          <p className="text-sm text-claude-text-muted">
            Drag and drop or click to select
          </p>
        </div>
      </div>
    </div>
  );
}
