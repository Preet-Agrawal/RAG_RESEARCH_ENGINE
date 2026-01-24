'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X } from 'lucide-react';
import type { PDFDocument } from '@/types';

interface PDFUploaderProps {
  onUpload: (file: File) => void;
  currentDocument?: PDFDocument | null;
  onRemove?: () => void;
}

export default function PDFUploader({ onUpload, currentDocument, onRemove }: PDFUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0]);
    }
    setIsDragging(false);
  }, [onUpload]);

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    onDragEnter: () => setIsDragging(true),
    onDragLeave: () => setIsDragging(false),
  });

  if (currentDocument) {
    return (
      <div className="flex items-center justify-between p-4 bg-claude-surface border border-claude-border rounded-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-claude-accent/10 rounded-lg">
            <File className="w-5 h-5 text-claude-accent" />
          </div>
          <div>
            <p className="text-sm font-medium text-claude-text">{currentDocument.name}</p>
            <p className="text-xs text-claude-text-secondary">
              {(currentDocument.size / 1024).toFixed(2)} KB
            </p>
          </div>
        </div>
        {onRemove && (
          <button
            onClick={onRemove}
            className="p-2 hover:bg-claude-bg rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-claude-text-secondary hover:text-claude-text" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
        transition-all duration-200
        ${isDragging
          ? 'border-claude-accent bg-claude-accent/5'
          : 'border-claude-border hover:border-claude-accent/50 hover:bg-claude-surface/50'
        }
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-4">
        <div className={`
          p-4 rounded-full transition-colors
          ${isDragging ? 'bg-claude-accent/20' : 'bg-claude-surface'}
        `}>
          <Upload className={`w-8 h-8 ${isDragging ? 'text-claude-accent' : 'text-claude-text-secondary'}`} />
        </div>
        <div>
          <p className="text-lg font-medium text-claude-text mb-2">
            {isDragging ? 'Drop your PDF here' : 'Upload PDF Document'}
          </p>
          <p className="text-sm text-claude-text-secondary">
            Drag and drop or click to select a PDF file
          </p>
        </div>
      </div>
    </div>
  );
}
