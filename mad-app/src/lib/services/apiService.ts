import type { AgentConfig, Message, AnalysisResult } from '$lib/types.ts';

const API_BASE = 'http://127.0.0.1:8000/api';

export interface SessionResponse {
    session_id: string;
    messages: Message[];
    error?: string;
}

export const startDebateSession = async (topic: string, agents: AgentConfig[]): Promise<SessionResponse> => {
    const response = await fetch(`${API_BASE}/start-debate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, agents_config: agents })
    });
    if (!response.ok) throw new Error('Failed to start session');
    return response.json();
};

export const continueDebateSession = async (session_id: string): Promise<SessionResponse> => {
    const response = await fetch(`${API_BASE}/continue-debate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id })
    });
    if (!response.ok) throw new Error('Failed to continue session');
    return response.json();
};

export const analyzeDebate = async (messages: Message[]): Promise<AnalysisResult> => {
    const response = await fetch(`${API_BASE}/analyze-debate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages })
    });
    return response.json();
};