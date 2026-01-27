'use client';

import React from "react"

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTender } from '@/app/context/TenderContext';
import { Upload, X, File, CheckCircle, AlertCircle } from 'lucide-react';

const PROCESSING_STAGES = ['Text Extraction', 'AI Analysis', 'Vector Embedding', 'Summarization'];
const MOCK_TENDERS = [
  {
    id: 't1',
    title: 'Advanced WTP System - Phase 3',
    location: 'Ahmedabad',
    valueInCrores: 165,
    emdInCrores: 3.3,
    category: 'WTP',
    contractType: 'O&M',
    duration: '5 years',
    deadlineDate: new Date(Date.now() + 40 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    tags: ['High O&M scope'],
    summary: 'Advanced water treatment facility with cutting-edge technology for Ahmedabad. Includes 5-year comprehensive O&M. Modern purification with dual-membrane systems.',
    priorityScore: 9.1,
    recommendation: 'Pursue',
    reasons: ['Highest value tender', 'Advanced technology opportunities', 'Strong revenue stream'],
    extractedFields: {
      tenderId: 'TEN-2024-007',
      publishDate: '2024-01-22',
      emails: ['advanced@ahmedabad.gov.in'],
      phones: ['+91-79-2111111'],
    },
    fullText: 'Advanced WTP System Phase 3...',
  },
];

export default function UploadPage() {
  const router = useRouter();
  const { uploadedFiles, addFile, removeFile, updateFileProgress, completeTenderProcessing } = useTender();
  const [isDragging, setIsDragging] = useState(false);
  const [processingState, setProcessingState] = useState<'idle' | 'processing' | 'complete'>('idle');
  const [uploadedPreviously, setUploadedPreviously] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const validateAndAddFiles = (files: FileList) => {
    const validFiles: File[] = [];
    let duplicates: string[] = [];

    Array.from(files).forEach(file => {
      if (!['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'].includes(file.type)) {
        // Invalid type - skip silently as per validation
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        // File too large - skip silently
        return;
      }
      
      if (uploadedFiles.some(f => f.name === file.name) || uploadedPreviously.includes(file.name)) {
        duplicates.push(file.name);
      } else {
        validFiles.push(file);
      }
    });

    if (duplicates.length > 0) {
      setUploadedPreviously(prev => [...new Set([...prev, ...duplicates])]);
    }

    validFiles.forEach(file => {
      const fileId = Math.random().toString(36).substr(2, 9);
      addFile({
        id: fileId,
        name: file.name,
        size: file.size,
        progress: 0,
        stage: 'Pending',
      });
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    validateAndAddFiles(e.dataTransfer.files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      validateAndAddFiles(e.target.files);
    }
  };

  const handleRemoveFile = (fileId: string) => {
    removeFile(fileId);
  };

  const simulateProcessing = async () => {
    setProcessingState('processing');

    for (const file of uploadedFiles) {
      for (const stage of PROCESSING_STAGES) {
        const startProgress = (PROCESSING_STAGES.indexOf(stage) / PROCESSING_STAGES.length) * 100;
        const endProgress = ((PROCESSING_STAGES.indexOf(stage) + 1) / PROCESSING_STAGES.length) * 100;

        for (let progress = startProgress; progress < endProgress; progress += Math.random() * 15) {
          updateFileProgress(file.id, Math.min(progress, endProgress - 1), stage);
          await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 700));
        }
        updateFileProgress(file.id, endProgress, stage);
      }
      updateFileProgress(file.id, 100, 'Complete');
    }

    // Simulate delay before completion
    await new Promise(resolve => setTimeout(resolve, 1500));
    setProcessingState('complete');
  };

  const handleStartProcessing = () => {
    if (uploadedFiles.length > 0) {
      simulateProcessing();
    }
  };

  const handleGoToDashboard = () => {
    completeTenderProcessing(MOCK_TENDERS);
    router.push('/dashboard');
  };

  return (
    <div className="min-h-screen bg-background">
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-foreground mb-2">Upload Tender Documents</h2>
          <p className="text-muted-foreground">
            Drag and drop PDF or DOCX files to extract tender information using AI
          </p>
        </div>

        {/* Duplicate Files Warning */}
        {uploadedPreviously.length > 0 && (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-amber-900 mb-1">Previously Uploaded Files</h3>
              <p className="text-sm text-amber-800 mb-2">
                The following files have already been uploaded in this session:
              </p>
              <div className="flex flex-wrap gap-2">
                {uploadedPreviously.map(filename => (
                  <span key={filename} className="text-xs bg-amber-100 text-amber-900 px-2 py-1 rounded">
                    {filename}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* File Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`mb-8 p-12 border-2 border-dashed rounded-xl transition-colors cursor-pointer ${
            isDragging
              ? 'border-primary bg-blue-50'
              : 'border-border bg-muted hover:border-primary hover:bg-blue-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx"
            onChange={handleFileSelect}
            className="hidden"
          />

          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Upload className="w-8 h-8 text-primary" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-foreground mb-1">
                {isDragging ? 'Drop files here' : 'Drag files here or click to browse'}
              </p>
              <p className="text-sm text-muted-foreground">
                Supports PDF and DOCX files (Max 50MB each)
              </p>
            </div>
          </div>
        </div>

        {/* Uploaded Files List */}
        {uploadedFiles.length > 0 && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-foreground mb-4">Uploaded Files ({uploadedFiles.length})</h3>
            <div className="space-y-3">
              {uploadedFiles.map(file => (
                <div
                  key={file.id}
                  className="p-4 border border-border rounded-lg bg-card hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3 flex-1">
                      <File className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-foreground truncate">{file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    {processingState !== 'processing' && (
                      <button
                        onClick={() => handleRemoveFile(file.id)}
                        className="p-1 hover:bg-muted rounded transition-colors flex-shrink-0"
                      >
                        <X className="w-5 h-5 text-muted-foreground" />
                      </button>
                    )}
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-2">
                    <div className="bg-muted rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-primary h-full transition-all duration-300"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  </div>

                  {/* Status */}
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{file.stage}</span>
                    <span className="font-medium text-foreground">{Math.round(file.progress)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Processing Stages Visualization */}
        {uploadedFiles.length > 0 && processingState !== 'idle' && (
          <div className="mb-8 p-6 border border-border rounded-lg bg-card">
            <h3 className="font-semibold text-foreground mb-4">Processing Pipeline</h3>
            <div className="flex items-center gap-4">
              {PROCESSING_STAGES.map((stage, idx) => (
                <div key={stage} className="flex items-center gap-4">
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all ${
                        uploadedFiles[0]?.progress >= ((idx + 1) / PROCESSING_STAGES.length) * 100
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground'
                      }`}
                    >
                      {uploadedFiles[0]?.progress >= ((idx + 1) / PROCESSING_STAGES.length) * 100 ? (
                        <CheckCircle className="w-5 h-5" />
                      ) : (
                        idx + 1
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground mt-2 text-center">{stage}</span>
                  </div>
                  {idx < PROCESSING_STAGES.length - 1 && (
                    <div className="flex-1 h-1 bg-muted rounded-full" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4">
          {processingState === 'idle' && uploadedFiles.length > 0 && (
            <button
              onClick={handleStartProcessing}
              className="px-6 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 transition-opacity"
            >
              Process Files
            </button>
          )}

          {processingState === 'complete' && (
            <div className="w-full">
              <div className="mb-6 p-6 bg-green-50 border border-green-200 rounded-lg flex gap-4">
                <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-green-900 mb-1">Processing Complete</h3>
                  <p className="text-sm text-green-800">
                    Successfully processed {uploadedFiles.length} file{uploadedFiles.length !== 1 ? 's' : ''}. 
                    New tenders are ready to view.
                  </p>
                </div>
              </div>

              <button
                onClick={handleGoToDashboard}
                className="w-full px-6 py-3 bg-primary text-primary-foreground rounded-lg font-semibold hover:opacity-90 transition-opacity text-center"
              >
                Go to Dashboard →
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
