'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTender, type Tender } from '@/app/context/TenderContext';
import { api } from '@/lib/api';
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileText,
  ChevronRight,
  FileSearch,
} from 'lucide-react';
import Loading from './loading';

type FieldValue = string | string[] | undefined;

const safeText = (value?: string) => {
  if (!value) return 'N/A';
  const v = value.trim();
  if (!v || v.toLowerCase() === 'n/a' || v.toLowerCase() === 'na') return 'N/A';
  return v;
};

const toList = (value?: FieldValue) => {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  return value.split(/[\n;,•]+/).map(v => v.trim()).filter(Boolean);
};

export default function DashboardPage() {
  const router = useRouter();
  const { filters, setSelectedTender } = useTender();
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedPanel, setExpandedPanel] = useState<Tender | null>(null);

  useEffect(() => {
    const fetchTenders = async () => {
      try {
        const data = await api.getTenders();
        setTenders(data as any);
      } catch (err) {
        console.error('Failed to fetch tenders', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchTenders();
  }, []);

  const handleAskAI = (tender: Tender) => {
    setSelectedTender(tender);
    router.push('/chat');
  };

  const handleMoreDetails = (tender: Tender) => {
    setExpandedPanel(tender);
  };

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
    return true;
  });

  const activeTender = expandedPanel || filteredTenders[0];
  const activeMeta = (activeTender?.extractedFields || {}) as Record<string, any>;

  const score = Math.min(100, Math.max(0, Math.round((activeTender?.priorityScore || 0) * 10)));
  const techScore = Math.min(98, Math.max(60, score + 8));
  const commercialRisk = Math.max(20, 100 - score);
  const resourceScore = Math.min(96, techScore + 6);
  const relationshipScore = Math.max(40, techScore - 20);

  const complianceItems = [
    ...toList(activeMeta.eligibility_summary).slice(0, 2),
    ...toList(activeMeta.required_documents).slice(0, 1),
  ].slice(0, 3);

  const criticalParams = [
    safeText(activeMeta.tender_value) !== 'N/A' ? `Value: ${safeText(activeMeta.tender_value)}` : null,
    safeText(activeMeta.emd) !== 'N/A' ? `EMD: ${safeText(activeMeta.emd)}` : null,
    safeText(activeMeta.submission_deadline) !== 'N/A' ? `Deadline: ${safeText(activeMeta.submission_deadline)}` : null,
    safeText(activeMeta.contract_duration) !== 'N/A' ? `Duration: ${safeText(activeMeta.contract_duration)}` : null,
  ].filter(Boolean) as string[];

  const keyRisks = (activeTender?.reasons || []).length
    ? activeTender?.reasons
    : toList(activeMeta?.eval?.key_risks);

  if (isLoading) {
    return <Loading />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl sm:text-4xl font-display font-semibold text-foreground">
          Tender Intelligence Engine
        </h1>
        <p className="text-muted-foreground text-lg">
          Welcome back. Here is what happened with your tenders today.
        </p>
      </div>

      <div className="grid xl:grid-cols-[2fr_1fr] gap-6">
        {/* Left column */}
        <div className="space-y-6">
          {activeTender ? (
            <div className="rounded-2xl border border-border bg-card shadow-sm p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-primary font-semibold mb-2">
                    Active Analysis
                  </p>
                  <h2 className="text-2xl font-display font-semibold text-foreground">
                    {activeTender.title}
                  </h2>
                  <p className="text-sm text-muted-foreground mt-2">
                    {safeText(activeMeta.issuing_authority)} | Ref: {safeText(activeMeta.tender_id)}
                  </p>
                </div>
                <span className="px-4 py-2 rounded-full text-sm font-semibold bg-emerald-100 text-emerald-700">
                  {activeTender.recommendation}
                </span>
              </div>

              <div className="mt-6 grid lg:grid-cols-2 gap-6">
                <div className="rounded-2xl border border-border bg-muted/40 p-5">
                  <div className="flex items-center gap-2 text-primary font-semibold mb-3">
                    <Sparkles className="w-4 h-4" />
                    AI-Generated Executive Summary
                  </div>
                  <p className="text-sm text-foreground/80 leading-relaxed">
                    {safeText(activeMeta.short_summary || activeTender.summary)}
                  </p>
                </div>
                <div className="grid gap-4">
                  <div className="rounded-2xl border border-border p-5">
                    <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-3">
                      Key Compliance PQR
                    </p>
                    <div className="space-y-3 text-sm">
                      {complianceItems.length > 0 ? (
                        complianceItems.map(item => (
                          <div key={item} className="flex items-start gap-2">
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5" />
                            <span>{item}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-muted-foreground">Eligibility details not available.</p>
                      )}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-border p-5">
                    <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-3">
                      Critical Parameters
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {criticalParams.length > 0 ? (
                        criticalParams.map(tag => (
                          <span key={tag} className="px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary">
                            {tag}
                          </span>
                        ))
                      ) : (
                        <p className="text-muted-foreground text-sm">No critical parameters detected yet.</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-border bg-card p-6 text-muted-foreground">
              No tenders available. Upload documents to start analysis.
            </div>
          )}

          {/* Processed package list */}
          <div className="rounded-2xl border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div>
                <h3 className="font-semibold text-foreground">Processed Package ({filteredTenders.length} Documents)</h3>
                <p className="text-sm text-muted-foreground">AI extraction confidence based on priority score.</p>
              </div>
              <button className="text-sm text-primary font-semibold">Download All Data</button>
            </div>
            <div className="divide-y divide-border">
              {filteredTenders.map(tender => (
                <div key={tender.id} className="flex items-center gap-4 px-6 py-4 hover:bg-muted/40">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-foreground">{tender.title}</p>
                    <p className="text-xs text-muted-foreground">{tender.location} • {tender.category}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-emerald-600">
                      {Math.min(100, Math.round((tender.priorityScore || 7) * 10))}%
                    </p>
                    <p className="text-xs text-muted-foreground">Extraction Confidence</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleMoreDetails(tender)}
                      className="px-3 py-2 text-xs font-semibold border border-border rounded-lg"
                    >
                      Details
                    </button>
                    <button
                      onClick={() => handleAskAI(tender)}
                      className="px-3 py-2 text-xs font-semibold bg-primary text-primary-foreground rounded-lg"
                    >
                      Ask Megha
                    </button>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          <div className="rounded-2xl border border-border bg-card shadow-sm p-6">
            <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground mb-4">
              <FileSearch className="w-4 h-4 text-primary" />
              Bid / No-Bid Intelligence
            </div>
            <div className="flex flex-col items-center gap-4">
              <div
                className="w-36 h-36 rounded-full flex items-center justify-center"
                style={{
                  background: `conic-gradient(var(--primary) ${score * 3.6}deg, var(--muted) 0deg)`,
                }}
              >
                <div className="w-28 h-28 rounded-full bg-card flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-foreground">{score}%</p>
                    <p className="text-xs text-muted-foreground">SCORE</p>
                  </div>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Recommendation: <span className="text-emerald-600 font-semibold">{activeTender?.recommendation || 'Review'}</span>
              </p>
            </div>

            <div className="mt-6 space-y-4">
              <Metric label="Technical Feasibility" value={techScore} color="bg-emerald-500" />
              <Metric label="Commercial Risk" value={commercialRisk} color="bg-amber-500" />
              <Metric label="Resource Availability" value={resourceScore} color="bg-emerald-500" />
              <Metric label="Client Relationship" value={relationshipScore} color="bg-blue-500" />
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card shadow-sm p-6 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-muted-foreground">Critical Alerts</p>
              <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-700">
                {keyRisks.length || 0} NEW
              </span>
            </div>
            {keyRisks.length ? (
              keyRisks.map((risk, idx) => (
                <div key={idx} className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  <AlertTriangle className="inline w-4 h-4 mr-2" />
                  {risk}
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No critical alerts detected.</p>
            )}
            <button className="w-full py-3 rounded-xl bg-slate-900 text-white font-semibold">
              Generate Full Bid Report
            </button>
          </div>
        </div>
      </div>

      {/* Details modal */}
      {expandedPanel && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            onClick={() => setExpandedPanel(null)}
          />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-4xl max-h-[85vh] overflow-y-auto rounded-2xl border border-border bg-card shadow-2xl p-6">
            <div className="flex items-start justify-between gap-4 pb-6 border-b border-border">
              <div>
                <h3 className="text-xl font-display font-semibold text-foreground">{expandedPanel.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {safeText(activeMeta.issuing_authority)} • {safeText(activeMeta.location)}
                </p>
              </div>
              <button
                onClick={() => setExpandedPanel(null)}
                className="px-3 py-2 text-sm rounded-lg border border-border"
              >
                Close
              </button>
            </div>

            <div className="mt-6 space-y-6">
              <DetailSection
                title="Tender Overview"
                fields={[
                  { label: 'Tender ID', value: activeMeta.tender_id },
                  { label: 'Category', value: activeMeta.category },
                  { label: 'Title', value: activeMeta.title },
                  { label: 'Location', value: activeMeta.location },
                  { label: 'Issuing Authority', value: activeMeta.issuing_authority },
                ]}
              />
              <DetailSection
                title="Dates & Duration"
                fields={[
                  { label: 'Publication Date', value: activeMeta.publication_date },
                  { label: 'Submission Deadline', value: activeMeta.submission_deadline },
                  { label: 'Bid Opening Date', value: activeMeta.bid_opening_date },
                  { label: 'Bid Opening Time', value: activeMeta.bid_opening_time },
                  { label: 'Contract Duration', value: activeMeta.contract_duration },
                ]}
              />
              <DetailSection
                title="Financials"
                fields={[
                  { label: 'Tender Value', value: activeMeta.tender_value },
                  { label: 'EMD', value: activeMeta.emd },
                  { label: 'Tender Fee', value: activeMeta.tender_fee },
                  { label: 'Performance Guarantee', value: activeMeta.performance_guarantee },
                ]}
              />
              <DetailSection
                title="Contacts"
                fields={[
                  { label: 'Contact Emails', value: activeMeta.contact_emails, isList: true },
                  { label: 'Contact Phones', value: activeMeta.contact_phones, isList: true },
                ]}
              />
              <DetailSection
                title="Scope & Summary"
                fields={[
                  { label: 'Scope of Work', value: activeMeta.scope_of_work, full: true },
                  { label: 'Short Summary', value: activeMeta.short_summary, full: true },
                  { label: 'Bidding Scope', value: activeMeta.bidding_scope, full: true },
                ]}
              />
              <DetailSection
                title="Eligibility & Criteria"
                fields={[
                  { label: 'Eligibility Summary', value: activeMeta.eligibility_summary, full: true },
                  { label: 'Exclusion Criteria', value: activeMeta.exclusion_criteria, full: true },
                  { label: 'Disqualification Criteria', value: activeMeta.disqualification_criteria, full: true },
                ]}
              />
              <DetailSection
                title="Documents & Deliverables"
                fields={[
                  { label: 'Required Documents', value: activeMeta.required_documents, full: true },
                  { label: 'Technical Documents', value: activeMeta.technical_documents, full: true },
                  { label: 'Deliverables', value: activeMeta.deliverables, full: true },
                ]}
              />
              <DetailSection
                title="Projects"
                fields={[
                  { label: 'Projects', value: activeMeta.projects, isList: true },
                ]}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-2">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold text-foreground">{value}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function DetailSection({
  title,
  fields,
}: {
  title: string;
  fields: { label: string; value: FieldValue; isList?: boolean; full?: boolean }[];
}) {
  return (
    <div className="rounded-2xl border border-border bg-muted/30 p-5">
      <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
        {title}
      </h4>
      <div className="grid sm:grid-cols-2 gap-4">
        {fields.map(field => {
          const isList = field.isList;
          const full = field.full;
          const value = field.value;
          const listItems = isList ? toList(value) : [];

          return (
            <div
              key={field.label}
              className={`rounded-xl border border-border bg-card p-4 ${full ? 'sm:col-span-2' : ''}`}
            >
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">
                {field.label}
              </p>
              {isList ? (
                listItems.length ? (
                  <div className="flex flex-wrap gap-2">
                    {listItems.map(item => (
                      <span key={item} className="px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
                        {item}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">N/A</p>
                )
              ) : (
                <p className="text-sm text-foreground/90 leading-relaxed">{safeText(String(value || ''))}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
