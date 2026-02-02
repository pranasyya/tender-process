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
                // Remove currency symbols, commas, 'Cr', etc
                const clean = str.replace(/[^\d.]/g, '');
                return parseFloat(clean) || 0;
            };

            // Helper to parse date to YYYY-MM-DD
            const parseDate = (str: string) => {
                if (!str) return new Date().toISOString().split('T')[0];
                // Expecting DD-MM-YYYY from backend
                const parts = str.split('-');
                if (parts.length === 3) {
                    // d-m-y to y-m-d
                    return `${parts[2]}-${parts[1]}-${parts[0]}`;
                }
                return str;
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
