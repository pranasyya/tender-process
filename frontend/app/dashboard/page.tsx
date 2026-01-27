'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSearchParams } from 'next/navigation';
import { useTender, type Tender } from '@/app/context/TenderContext';
import {
  Search,
  X,
  Filter,
  MapPin,
  Calendar,
  MessageCircle,
  Info,
  Droplet,
  Factory,
  Building2,
  TrendingUp,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';
import Loading from './loading';

export default function DashboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { tenders, filters, setFilters, selectedTender, setSelectedTender } = useTender();
  const [expandedPanel, setExpandedPanel] = useState<Tender | null>(null);

  const handleAskAI = (tender: Tender) => {
    setSelectedTender(tender);
    router.push('/chat');
  };

  const handleMoreDetails = (tender: Tender) => {
    setExpandedPanel(tender);
  };

  // Filter logic
  const filteredTenders = tenders.filter(tender => {
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      if (
        !tender.title.toLowerCase().includes(query) &&
        !tender.location.toLowerCase().includes(query)
      ) {
        return false;
      }
    }

    if (filters.location !== 'All' && tender.location !== filters.location) {
      return false;
    }

    if (filters.valueRange !== 'All') {
      const value = tender.valueInCrores;
      if (filters.valueRange === '<50' && value >= 50) return false;
      if (filters.valueRange === '50-100' && (value < 50 || value > 100)) return false;
      if (filters.valueRange === '100-200' && (value < 100 || value > 200)) return false;
      if (filters.valueRange === '>200' && value <= 200) return false;
    }

    if (filters.contractType !== 'All' && !tender.contractType.includes(filters.contractType)) {
      return false;
    }

    if (filters.deadline !== 'All') {
      const deadlineDate = new Date(tender.deadlineDate);
      const now = new Date();
      const daysUntilDeadline = Math.ceil((deadlineDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

      if (filters.deadline === '30' && daysUntilDeadline > 30) return false;
      if (filters.deadline === '60' && daysUntilDeadline > 60) return false;
      if (filters.deadline === '90' && daysUntilDeadline > 90) return false;
    }

    return true;
  });

  const getCategoryIcon = (category: string) => {
    if (category.includes('WTP') || category.includes('Water Treatment'))
      return <Droplet className="w-6 h-6" />;
    if (category.includes('CETP') || category.includes('Industrial'))
      return <Factory className="w-6 h-6" />;
    return <Building2 className="w-6 h-6" />;
  };

  const getActiveFilters = () => {
    const active = [];
    if (filters.searchQuery) active.push(filters.searchQuery);
    if (filters.location !== 'All') active.push(filters.location);
    if (filters.valueRange !== 'All') active.push(`₹${filters.valueRange}Cr`);
    if (filters.contractType !== 'All') active.push(filters.contractType);
    if (filters.deadline !== 'All') active.push(`${filters.deadline} days`);
    return active;
  };

  return (
    <div className="min-h-screen bg-background">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-8">
          <h2 className="text-4xl font-bold text-foreground mb-2">Available Tenders</h2>
          <p className="text-muted-foreground text-lg">
            Showing <span className="font-semibold text-foreground">{filteredTenders.length}</span> of <span className="font-semibold text-foreground">{tenders.length}</span> tenders
          </p>
        </div>

        {/* Search and Filters */}
        <div className="mb-6 space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by title or location..."
              value={filters.searchQuery}
              onChange={e => setFilters({ searchQuery: e.target.value })}
              className="w-full pl-12 pr-4 py-3 border border-border rounded-xl bg-card focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200"
            />
          </div>

          {/* Filter Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <select
              value={filters.location}
              onChange={e => setFilters({ location: e.target.value })}
              className="px-4 py-2 border border-border rounded-xl bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200"
            >
              <option value="All">All Locations</option>
              <option value="Ahmedabad">Ahmedabad</option>
              <option value="Surat">Surat</option>
              <option value="Vadodara">Vadodara</option>
            </select>

            <select
              value={filters.valueRange}
              onChange={e => setFilters({ valueRange: e.target.value })}
              className="px-4 py-2 border border-border rounded-xl bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200"
            >
              <option value="All">All Values</option>
              <option value="<50">Less than ₹50Cr</option>
              <option value="50-100">₹50-100 Cr</option>
              <option value="100-200">₹100-200 Cr</option>
              <option value=">200">Greater than ₹200 Cr</option>
            </select>

            <select
              value={filters.contractType}
              onChange={e => setFilters({ contractType: e.target.value })}
              className="px-4 py-2 border border-border rounded-xl bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200"
            >
              <option value="All">All Contract Types</option>
              <option value="O&M">O&M</option>
              <option value="EPC">EPC</option>
              <option value="Design-Build">Design-Build</option>
            </select>

            <select
              value={filters.deadline}
              onChange={e => setFilters({ deadline: e.target.value })}
              className="px-4 py-2 border border-border rounded-xl bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200"
            >
              <option value="All">All Deadlines</option>
              <option value="30">Next 30 days</option>
              <option value="60">Next 60 days</option>
              <option value="90">Next 90 days</option>
            </select>

            <button
              onClick={() =>
                setFilters({
                  searchQuery: '',
                  location: 'All',
                  valueRange: 'All',
                  contractType: 'All',
                  deadline: 'All',
                })
              }
              className="px-4 py-2 border border-border rounded-xl bg-card text-sm hover:bg-muted transition-colors duration-200 font-medium"
            >
              Clear Filters
            </button>
          </div>

          {/* Active Filters */}
          {getActiveFilters().length > 0 && (
            <div className="flex flex-wrap gap-2">
              {getActiveFilters().map(filter => (
                <span
                  key={filter}
                  className="px-3 py-1 bg-primary/10 text-primary text-sm rounded-full flex items-center gap-2"
                >
                  {filter}
                  <X className="w-3 h-3" />
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Tender Cards */}
          <div className="lg:col-span-3">
            {filteredTenders.length === 0 ? (
              <div className="p-8 text-center border border-border rounded-lg bg-card">
                <AlertCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-foreground font-medium mb-1">No tenders found</p>
                <p className="text-muted-foreground text-sm">Try adjusting your filters</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredTenders.map(tender => (
                  <div
                    key={tender.id}
                    className="p-6 border border-border rounded-xl bg-card hover:shadow-lg hover:border-primary/50 transition-all duration-300 group"
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                        {getCategoryIcon(tender.category)}
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-foreground">₹{tender.valueInCrores} Cr</p>
                        <p className="text-xs text-muted-foreground">EMD: ₹{tender.emdInCrores} Cr</p>
                      </div>
                    </div>

                    {/* Title */}
                    <h3 className="font-bold text-foreground mb-3 line-clamp-2 leading-snug">
                      {tender.title}
                    </h3>

                    {/* Details */}
                    <div className="space-y-2 mb-4 text-sm">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <MapPin className="w-4 h-4 flex-shrink-0" />
                        <span>{tender.location}</span>
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Calendar className="w-4 h-4 flex-shrink-0" />
                        <span>{new Date(tender.deadlineDate).toLocaleDateString()}</span>
                      </div>
                      <div className="text-muted-foreground">
                        <span>{tender.contractType}, {tender.duration}</span>
                      </div>
                    </div>

                    {/* Tags */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {tender.tags.map(tag => (
                        <span
                          key={tag}
                          className={`text-xs px-3 py-1 rounded-full font-semibold ${
                            tag === 'High O&M scope'
                              ? 'bg-primary/20 text-primary border border-primary/30'
                              : 'bg-secondary/20 text-secondary border border-secondary/30'
                          }`}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>

                    {/* Buttons */}
                    <div className="flex gap-2 pt-2">
                      <button
                        onClick={() => handleMoreDetails(tender)}
                        className="flex-1 px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-muted hover:border-primary/50 transition-all duration-200"
                      >
                        More Details
                      </button>
                      <button
                        onClick={() => handleAskAI(tender)}
                        className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:shadow-lg hover:shadow-primary/30 transition-all duration-200 flex items-center justify-center gap-2"
                      >
                        <MessageCircle className="w-4 h-4" />
                        Ask Megha
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Panel - AI Recommendation & Details */}
          <div className="space-y-6">
            {/* AI Recommendation Box */}
            <div className="p-6 border border-primary/20 rounded-xl bg-gradient-to-br from-primary/5 to-primary/10 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                  <TrendingUp className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-bold text-foreground mb-2">Megha AI Insights</h3>
                  <p className="text-sm text-foreground/80 leading-relaxed">
                    Focus on Ahmedabad and Surat projects due to higher O&M potential. Vadodara EPC-only projects have limited long-term revenue opportunities.
                  </p>
                </div>
              </div>
            </div>

            {/* Selected Tender Details Panel */}
            {expandedPanel && (
              <div
                className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
                onClick={() => setExpandedPanel(null)}
              />
            )}

            <div
              className={`${
                expandedPanel 
                  ? 'fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-2xl max-h-[80vh] overflow-y-auto'
                  : 'hidden lg:block'
              } p-8 border border-white/20 rounded-2xl bg-card/80 backdrop-blur-xl shadow-2xl`}
            >
              {expandedPanel ? (
                <>
                  <div className="flex items-start justify-between mb-6 pb-6 border-b border-white/10">
                    <div className="flex-1 pr-4">
                      <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center text-primary mb-3">
                        {getCategoryIcon(expandedPanel.category)}
                      </div>
                      <h3 className="font-bold text-xl text-foreground">{expandedPanel.title}</h3>
                      <p className="text-sm text-muted-foreground mt-1">{expandedPanel.category}</p>
                    </div>
                    <button
                      onClick={() => setExpandedPanel(null)}
                      className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                    >
                      <X className="w-5 h-5 text-foreground" />
                    </button>
                  </div>

                  <div className="space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-xl bg-primary/10 border border-primary/20">
                        <p className="text-xs text-muted-foreground uppercase font-semibold mb-2">
                          Tender Value
                        </p>
                        <p className="font-bold text-lg text-primary">
                          ₹{expandedPanel.valueInCrores} Cr
                        </p>
                      </div>
                      <div className="p-4 rounded-xl bg-secondary/10 border border-secondary/20">
                        <p className="text-xs text-muted-foreground uppercase font-semibold mb-2">
                          EMD Amount
                        </p>
                        <p className="font-bold text-lg text-secondary">
                          ₹{expandedPanel.emdInCrores} Cr
                        </p>
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <p className="text-xs text-muted-foreground uppercase font-semibold mb-2">
                        Location
                      </p>
                      <p className="text-foreground font-medium flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-primary" />
                        {expandedPanel.location}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                        <p className="text-xs text-muted-foreground uppercase font-semibold mb-2">
                          Deadline
                        </p>
                        <p className="text-foreground font-medium flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-accent" />
                          {new Date(expandedPanel.deadlineDate).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                        <p className="text-xs text-muted-foreground uppercase font-semibold mb-2">
                          Tender ID
                        </p>
                        <p className="text-foreground font-mono text-sm truncate">
                          {expandedPanel.extractedFields.tenderId}
                        </p>
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <p className="text-xs text-muted-foreground uppercase font-semibold mb-3">
                        Project Summary
                      </p>
                      <p className="text-sm text-foreground leading-relaxed">
                        {expandedPanel.summary}
                      </p>
                    </div>

                    <div className="p-4 rounded-xl bg-gradient-to-br from-primary/15 to-secondary/15 border border-primary/30">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="text-xs text-muted-foreground uppercase font-semibold mb-2">
                            Megha AI Recommendation
                          </p>
                          <p className="font-bold text-lg text-primary mb-1">{expandedPanel.recommendation}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-primary">{expandedPanel.priorityScore}</p>
                          <p className="text-xs text-muted-foreground">Priority Score</p>
                        </div>
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <p className="text-xs text-muted-foreground uppercase font-semibold mb-3">
                        Key Reasons
                      </p>
                      <ul className="space-y-2">
                        {expandedPanel.reasons.map((reason, idx) => (
                          <li key={idx} className="text-sm text-foreground flex gap-3">
                            <span className="text-primary font-bold text-lg flex-shrink-0">✓</span>
                            <span>{reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <Info className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">
                    Click "More Details" on any tender to view full information
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
