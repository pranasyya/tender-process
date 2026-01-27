'use client';

import React, { createContext, useContext, useState, useCallback, useReducer } from 'react';

export interface Tender {
  id: string;
  title: string;
  location: string;
  valueInCrores: number;
  emdInCrores: number;
  category: string;
  contractType: string;
  duration: string;
  deadlineDate: string;
  tags: string[];
  summary: string;
  priorityScore: number;
  recommendation: string;
  reasons: string[];
  extractedFields: {
    tenderId: string;
    publishDate: string;
    emails: string[];
    phones: string[];
  };
  fullText: string;
}

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  progress: number;
  stage: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Array<{ tenderName: string; page: number }>;
}

interface TenderContextType {
  // Upload state
  uploadedFiles: UploadedFile[];
  tenders: Tender[];
  processedCount: number;
  
  // Upload actions
  addFile: (file: UploadedFile) => void;
  removeFile: (fileId: string) => void;
  updateFileProgress: (fileId: string, progress: number, stage: string) => void;
  completeTenderProcessing: (newTenders: Tender[]) => void;
  
  // Dashboard state
  selectedTender: Tender | null;
  setSelectedTender: (tender: Tender | null) => void;
  
  // Chat state
  chatHistory: ChatMessage[];
  selectedTenderContext: Tender | null;
  addChatMessage: (message: ChatMessage) => void;
  setSelectedTenderContext: (tender: Tender | null) => void;
  
  // Filter state
  filters: {
    searchQuery: string;
    location: string;
    valueRange: string;
    contractType: string;
    deadline: string;
  };
  setFilters: (filters: Partial<TenderContextType['filters']>) => void;
}

const TenderContext = createContext<TenderContextType | undefined>(undefined);

export function TenderProvider({ children }: { children: React.ReactNode }) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [tenders, setTenders] = useState<Tender[]>(getMockTenders());
  const [processedCount, setProcessedCount] = useState(0);
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [selectedTenderContext, setSelectedTenderContext] = useState<Tender | null>(null);
  const [filters, setFiltersState] = useState({
    searchQuery: '',
    location: 'All',
    valueRange: 'All',
    contractType: 'All',
    deadline: 'All',
  });

  const addFile = useCallback((file: UploadedFile) => {
    setUploadedFiles(prev => [...prev, file]);
  }, []);

  const removeFile = useCallback((fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  }, []);

  const updateFileProgress = useCallback((fileId: string, progress: number, stage: string) => {
    setUploadedFiles(prev =>
      prev.map(f => (f.id === fileId ? { ...f, progress, stage } : f))
    );
  }, []);

  const completeTenderProcessing = useCallback((newTenders: Tender[]) => {
    setTenders(prev => [...newTenders, ...prev]);
    setProcessedCount(prev => prev + newTenders.length);
    setUploadedFiles([]);
  }, []);

  const addChatMessage = useCallback((message: ChatMessage) => {
    setChatHistory(prev => [...prev, message]);
  }, []);

  const setFilters = useCallback((newFilters: Partial<TenderContextType['filters']>) => {
    setFiltersState(prev => ({ ...prev, ...newFilters }));
  }, []);

  const value: TenderContextType = {
    uploadedFiles,
    tenders,
    processedCount,
    addFile,
    removeFile,
    updateFileProgress,
    completeTenderProcessing,
    selectedTender,
    setSelectedTender,
    chatHistory,
    selectedTenderContext,
    addChatMessage,
    setSelectedTenderContext,
    filters,
    setFilters,
  };

  return <TenderContext.Provider value={value}>{children}</TenderContext.Provider>;
}

export function useTender() {
  const context = useContext(TenderContext);
  if (!context) {
    throw new Error('useTender must be used within TenderProvider');
  }
  return context;
}

function getMockTenders(): Tender[] {
  const baseDate = new Date();
  
  return [
    {
      id: '1',
      title: 'Development of 50 MLD Water Treatment Plant with 5 years O&M',
      location: 'Ahmedabad',
      valueInCrores: 145,
      emdInCrores: 2.9,
      category: 'WTP',
      contractType: 'O&M',
      duration: '5 years',
      deadlineDate: new Date(baseDate.getTime() + 25 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      tags: ['High O&M scope'],
      summary: 'This tender seeks to develop a modern 50 MLD water treatment plant with comprehensive operation and maintenance services for 5 years. The project includes state-of-the-art treatment facilities with advanced purification systems. It covers regular maintenance, monitoring, and optimization of all plant operations. The successful bidder will be responsible for ensuring 24/7 plant availability and maintaining quality standards.',
      priorityScore: 9.2,
      recommendation: 'Pursue',
      reasons: ['High O&M scope indicates long-term revenue', 'Significant project value', 'Aligned with our expertise'],
      extractedFields: {
        tenderId: 'TEN-2024-001',
        publishDate: '2024-01-15',
        emails: ['procurement@ahmedabad.gov.in'],
        phones: ['+91-79-2123456'],
      },
      fullText: 'Development of 50 MLD Water Treatment Plant with 5 years Operation and Maintenance...',
    },
    {
      id: '2',
      title: 'Construction of 40 MLD CETP with 10 years O&M',
      location: 'Surat',
      valueInCrores: 110,
      emdInCrores: 2.2,
      category: 'CETP',
      contractType: 'O&M',
      duration: '10 years',
      deadlineDate: new Date(baseDate.getTime() + 35 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      tags: ['High O&M scope'],
      summary: 'This Common Effluent Treatment Plant (CETP) project serves multiple industries in the Surat region. The facility will treat 40 MLD of industrial wastewater with comprehensive 10-year O&M coverage. The project includes modern treatment technologies, environmental monitoring systems, and compliance with all regulatory standards. Long-term operational support ensures sustainable industrial wastewater management.',
      priorityScore: 8.8,
      recommendation: 'Pursue',
      reasons: ['10-year O&M contract provides stable revenue', 'Growing industrial base in Surat', 'High market demand'],
      extractedFields: {
        tenderId: 'TEN-2024-002',
        publishDate: '2024-01-20',
        emails: ['tenders@suratmunicipal.org'],
        phones: ['+91-261-2123456'],
      },
      fullText: 'Construction of 40 MLD Common Effluent Treatment Plant with 10 years Operation and Maintenance...',
    },
    {
      id: '3',
      title: 'River Intake Structure and WTP Development',
      location: 'Vadodara',
      valueInCrores: 125,
      emdInCrores: 2.5,
      category: 'Water Infrastructure',
      contractType: 'EPC',
      duration: 'N/A',
      deadlineDate: new Date(baseDate.getTime() + 45 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      tags: ['EPC only'],
      summary: 'This project focuses on developing comprehensive water intake infrastructure from river sources and establishing associated water treatment facilities. The scope includes design, engineering, procurement, and construction of intake structures with minimal environmental impact. The project requires specialized expertise in riverine engineering and environmental compliance. This is a fixed-price EPC contract without operational maintenance responsibilities.',
      priorityScore: 7.5,
      recommendation: 'Consider',
      reasons: ['EPC-only limits long-term revenue', 'Specialized technical expertise required', 'Strong engineering team needed'],
      extractedFields: {
        tenderId: 'TEN-2024-003',
        publishDate: '2024-01-18',
        emails: ['projects@vadodaracity.org'],
        phones: ['+91-265-2123456'],
      },
      fullText: 'River Intake Structure and Water Treatment Plant Development - Design, Engineering, Procurement and Construction...',
    },
    {
      id: '4',
      title: 'Sewage Treatment Plant Expansion - Phase 2',
      location: 'Ahmedabad',
      valueInCrores: 95,
      emdInCrores: 1.9,
      category: 'STP',
      contractType: 'EPC',
      duration: '3 years',
      deadlineDate: new Date(baseDate.getTime() + 20 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      tags: ['Urban Infrastructure'],
      summary: 'Expansion of existing sewage treatment capacity to handle 200 MLD of municipal wastewater. This phase 2 project includes additional treatment trains and tertiary treatment systems. The contract covers design and construction of modern treatment facilities with advanced automation and environmental monitoring. Timeline: 3 years for design and construction.',
      priorityScore: 8.0,
      recommendation: 'Pursue',
      reasons: ['Municipal infrastructure growth', 'Proven technology deployment', 'Government priority sector'],
      extractedFields: {
        tenderId: 'TEN-2024-004',
        publishDate: '2024-01-17',
        emails: ['stp@ahmedabad.gov.in'],
        phones: ['+91-79-2654321'],
      },
      fullText: 'Sewage Treatment Plant Expansion Phase 2 - 200 MLD capacity enhancement...',
    },
    {
      id: '5',
      title: 'Water Supply Network Rehabilitation',
      location: 'Vadodara',
      valueInCrores: 78,
      emdInCrores: 1.56,
      category: 'Water Distribution',
      contractType: 'EPC',
      duration: '2 years',
      deadlineDate: new Date(baseDate.getTime() + 55 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      tags: ['Pipeline Infrastructure'],
      summary: 'Comprehensive rehabilitation of aging water supply distribution network covering 500 km of pipelines. The project includes pipe replacement, leak detection, and system optimization. Advanced GIS-based monitoring systems will be installed for real-time network management. The contract focuses on reducing non-revenue water losses in the city distribution system.',
      priorityScore: 7.8,
      recommendation: 'Consider',
      reasons: ['Infrastructure maintenance rather than growth', 'Significant logistics complexity', 'Long project duration'],
      extractedFields: {
        tenderId: 'TEN-2024-005',
        publishDate: '2024-01-19',
        emails: ['waterworks@vadodara.org'],
        phones: ['+91-265-2987654'],
      },
      fullText: 'Water Supply Network Rehabilitation and upgradation of distribution system...',
    },
    {
      id: '6',
      title: 'Industrial Park Wastewater Management System',
      location: 'Surat',
      valueInCrores: 88,
      emdInCrores: 1.76,
      category: 'Industrial Wastewater',
      contractType: 'O&M',
      duration: '7 years',
      deadlineDate: new Date(baseDate.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      tags: ['Industrial Management'],
      summary: 'Development and management of comprehensive wastewater treatment system for a major industrial park. The system will treat diverse industrial effluents with multiple treatment trains for different waste streams. 7-year O&M contract includes environmental compliance, regular monitoring, and waste management. Specialized expertise in handling textile, chemical, and manufacturing industry wastewater.',
      priorityScore: 8.5,
      recommendation: 'Pursue',
      reasons: ['Specialized industrial expertise required', 'Long-term O&M contract', 'Growing industrial sector demand'],
      extractedFields: {
        tenderId: 'TEN-2024-006',
        publishDate: '2024-01-21',
        emails: ['industrial@suratpark.org'],
        phones: ['+91-261-2789456'],
      },
      fullText: 'Industrial Park Integrated Wastewater Management and Treatment System...',
    },
  ];
}
