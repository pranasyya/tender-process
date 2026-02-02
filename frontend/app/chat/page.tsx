'use client';

import { useState, useRef, useEffect } from 'react';
import { useTender, type ChatMessage } from '@/app/context/TenderContext';
import { api } from '@/lib/api';
import {
  Send,
  X,
  Loader2,
  Clock,
  MessageCircle,
} from 'lucide-react';


const SUGGESTED_QUESTIONS = [
  'What are the O&M requirements for Ahmedabad WTP?',
  'Compare EMD amounts across all tenders',
  'Which tenders have the earliest deadlines?',
  "What's included in the Surat CETP scope?",
];

const MOCK_AI_RESPONSES: Record<string, string> = {
  'O&M': 'The O&M (Operation & Maintenance) requirements vary by location. Ahmedabad WTP requires 5 years of continuous operations with 24/7 monitoring. Surat CETP has 10 years of O&M coverage with specialized industrial wastewater management. These contracts emphasize equipment maintenance, staff training, and regulatory compliance.',
  'EMD': 'EMD (Earnest Money Deposit) amounts across all tenders: Ahmedabad WTP: ₹2.9 Cr, Surat CETP: ₹2.2 Cr, Vadodara: ₹2.5 Cr, Ahmedabad STP: ₹1.9 Cr, Vadodara Network: ₹1.56 Cr, Surat Industrial: ₹1.76 Cr. Generally, higher-value projects require proportionally higher EMD.',
  'deadline': 'Earliest deadlines: Ahmedabad WTP (25 days), Ahmedabad STP (20 days), Surat WTP (35 days), Surat Industrial (30 days), Vadodara WTP (45 days), Vadodara Network (55 days). Plan your bid submissions accordingly.',
  'scope': 'The Surat CETP handles 40 MLD of industrial wastewater with advanced treatment technologies. The scope includes primary treatment, secondary biological treatment, tertiary polishing, and sludge management. The 10-year O&M contract covers equipment maintenance, monitoring, optimization, and regulatory compliance for industrial park operations.',
};

export default function ChatPage() {
  const { chatHistory, selectedTenderContext, addChatMessage, setSelectedTenderContext, tenders } = useTender();
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [localChatHistory, setLocalChatHistory] = useState<ChatMessage[]>(chatHistory);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [localChatHistory]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (message?: string) => {
    const messageText = message || inputValue.trim();

    if (!messageText) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substr(2, 9),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    };

    setLocalChatHistory(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Construct query with context if available
      let finalQuery = messageText;
      if (selectedTenderContext) {
        finalQuery = `Context: Tender "${selectedTenderContext.title}" (ID: ${selectedTenderContext.id}). \nQuestion: ${messageText}`;
      }

      const data = await api.chatWithAI(finalQuery);

      const aiResponse: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        sources: data.context ? data.context.map((c: any) => ({
          tenderName: c.meta.title || 'Unknown',
          page: 1 // Backend might not return page num yet
        })) : undefined
      };
      setLocalChatHistory(prev => [...prev, aiResponse]);
    } catch (err) {
      console.error("Chat error", err);
      const errorMsg: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        role: 'assistant',
        content: "Sorry, I'm having trouble connecting to the server.",
        timestamp: new Date(),
      };
      setLocalChatHistory(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      scrollToBottom();
    }
  };

  const handleSuggestedQuestion = (question: string) => {
    handleSendMessage(question);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <main className="flex-1 flex overflow-hidden">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Tender Context Header */}
          <div className="border-b border-border bg-card p-6 shadow-sm">
            <div className="max-w-4xl mx-auto">
              {selectedTenderContext ? (
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase font-semibold mb-1">
                      Megha Context
                    </p>
                    <p className="font-medium text-foreground line-clamp-1">
                      {selectedTenderContext.title} - ₹{selectedTenderContext.valueInCrores} Cr
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedTenderContext(null)}
                    className="px-4 py-2 text-sm border border-border rounded-lg hover:bg-muted hover:border-primary/50 transition-all duration-200 flex items-center gap-2 flex-shrink-0"
                  >
                    Clear
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <MessageCircle className="w-5 h-5 text-primary" />
                  </div>
                  <p className="text-foreground font-medium">Ask Megha about any tender details</p>
                </div>
              )}
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto w-full p-4">
              {localChatHistory.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center py-12">
                  <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
                    <MessageCircle className="w-8 h-8 text-primary" />
                  </div>
                  <p className="text-foreground font-bold text-xl mb-2">Talk to Megha</p>
                  <p className="text-muted-foreground text-sm mb-10 max-w-sm text-center">
                    Ask questions about tender details, deadlines, requirements, or get strategic recommendations
                  </p>

                  {/* Suggested Questions */}
                  <div className="w-full max-w-2xl">
                    <p className="text-xs text-muted-foreground uppercase font-semibold mb-4">
                      Try these questions
                    </p>
                    <div className="grid grid-cols-1 gap-3">
                      {SUGGESTED_QUESTIONS.map((question, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSuggestedQuestion(question)}
                          className="p-4 text-left border border-border rounded-xl hover:border-primary hover:bg-primary/5 transition-all duration-200 text-sm text-foreground font-medium hover:shadow-sm"
                        >
                          {question}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4 py-4">
                  {localChatHistory.map(message => (
                    <div
                      key={message.id}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in duration-300`}
                    >
                      <div
                        className={`max-w-xl px-5 py-3 rounded-xl shadow-sm ${message.role === 'user'
                          ? 'bg-primary text-primary-foreground rounded-br-none'
                          : 'bg-muted text-foreground rounded-bl-none border border-border/50'
                          }`}
                      >
                        <p className="text-sm leading-relaxed">{message.content}</p>
                        <p className={`text-xs mt-2 ${message.role === 'user' ? 'opacity-70' : 'opacity-60'}`}>
                          {formatTime(message.timestamp)}
                        </p>

                        {message.sources && message.sources.length > 0 && (
                          <div className={`mt-3 pt-3 border-t ${message.role === 'user' ? 'border-primary/20' : 'border-border/50'}`}>
                            <p className="text-xs opacity-70 font-semibold mb-1">Sources:</p>
                            {message.sources.map((source, idx) => (
                              <p key={idx} className="text-xs opacity-70">
                                {source.tenderName.substring(0, 40)}... (Page {source.page})
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {isLoading && (
                    <div className="flex justify-start animate-in fade-in duration-300">
                      <div className="bg-muted px-5 py-3 rounded-xl border border-border/50 flex items-center gap-3 shadow-sm">
                        <Loader2 className="w-4 h-4 animate-spin text-primary" />
                        <span className="text-sm text-foreground font-medium">Megha is thinking...</span>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </div>

          {/* Input Area */}
          <div className="border-t border-border bg-card p-6 shadow-lg">
            <div className="max-w-4xl mx-auto">
              <div className="flex gap-3">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  onKeyPress={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder="Ask Megha about tender details, deadlines, requirements..."
                  disabled={isLoading}
                  className="flex-1 px-5 py-3 border border-border rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50 transition-all duration-200"
                />
                <button
                  onClick={() => handleSendMessage()}
                  disabled={isLoading || !inputValue.trim()}
                  className="px-5 py-3 bg-primary text-primary-foreground rounded-xl hover:shadow-lg hover:shadow-primary/30 transition-all duration-200 disabled:opacity-50 flex items-center gap-2 font-medium"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
