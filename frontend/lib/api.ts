import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export interface Tender {
    id: string;
    title: string;
    location: string;
    valueInCrores: number; // Parsed from string
    emdInCrores: number;   // Parsed from string
    category: string;
    contractType: string;
    duration: string;
    deadlineDate: string;  // YYYY-MM-DD
    tags: string[];
    summary: string;
    priorityScore: number;
    recommendation: string;
    reasons: string[];
    extractedFields: any;
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    sources?: { tenderName: string; page: number }[];
}

export const api = {
    /**
     * Upload files for analysis
     */
    uploadFiles: async (files: File[]) => {
        const formData = new FormData();
        files.forEach((file) => {
            formData.append('files', file);
        });

        const response = await axios.post(`${API_BASE_URL}/analyse`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    /**
     * Get processing progress
     */
    getProgress: async () => {
        const response = await axios.get(`${API_BASE_URL}/progress`);
        return response.data;
    },

    /**
     * Fetch all processed tenders
     */
    getTenders: async (): Promise<Tender[]> => {
        const response = await axios.get(`${API_BASE_URL}/tenders`);
        const rawData = response.data;

        // Transform backend data to frontend Tender interface
        return rawData.map((item: any) => {
            // Helper to parse currency strings to numbers
            const parseCurrency = (str: string) => {
                if (!str) return 0;
                const s = String(str).toLowerCase().trim();
                if (!s || s === 'n/a' || s === 'na') return 0;
                const numMatch = s.match(/[\d,.]+/);
                if (!numMatch) return 0;
                const num = parseFloat(numMatch[0].replace(/,/g, ''));
                if (Number.isNaN(num)) return 0;

                // Unit-aware conversion to crores
                if (/\bcr\b|crore|crores/.test(s)) return num;
                if (/lakh|lakhs|lac|lacs/.test(s)) return num / 100;
                if (/million/.test(s)) return num / 10;   // 1 million = 0.1 crore
                if (/billion/.test(s)) return num * 100;  // 1 billion = 100 crore
                if (/thousand|k\b/.test(s)) return num / 100000;

                // If currency symbol present, assume rupees
                if (/₹|rs\.?/.test(s)) return num / 1e7;

                // Fallback: treat large numbers as rupees
                if (num >= 100000) return num / 1e7;

                // Otherwise assume already in crores
                return num;
            };

            // Helper to parse date to YYYY-MM-DD
            const parseDate = (str: string) => {
                if (!str) return '';
                const s = String(str).trim();
                if (!s || s.toLowerCase() === 'n/a' || s.toLowerCase() === 'na') return '';
                if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
                const parts = s.split(/[-/]/);
                if (parts.length === 3) {
                    const [d, m, y] = parts;
                    const yy = y.length === 2 ? `20${y}` : y;
                    return `${yy}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
                }
                return '';
            };

            const meta = item || {};

            // Determine tags based on content
            const tags = [];
            if (typeof meta.scope_of_work === 'string' && meta.scope_of_work.toLowerCase().includes('o&m')) {
                tags.push('High O&M scope');
            }

            return {
                id: meta.tender_id || Math.random().toString(36).substr(2, 9),
                title: meta.title || 'Untitled Tender',
                location: meta.location || 'Unknown Location',
                valueInCrores: parseCurrency(meta.tender_value),
                emdInCrores: parseCurrency(meta.emd),
                category: meta.category || 'General',
                contractType: meta.contract_duration ? 'O&M' : 'EPC', // Heuristic
                duration: meta.contract_duration || 'N/A',
                deadlineDate: parseDate(meta.submission_deadline),
                tags: tags,
                summary: meta.short_summary || meta.scope_of_work || '',
                priorityScore: (meta.eval && meta.eval.priority_score) ? parseFloat(meta.eval.priority_score) : 8.5,
                recommendation: (meta.eval && meta.eval.recommendation) ? meta.eval.recommendation : 'Review',
                reasons: (meta.eval && meta.eval.key_risks) ? [meta.eval.key_risks] : [],
                extractedFields: meta, // Store full raw metadata here
            };
        });
    },

    /**
     * Chat with AI about tenders
     */
    chatWithAI: async (query: string) => {
        const response = await axios.post(`${API_BASE_URL}/chat`, { query });
        return response.data;
    },
};
