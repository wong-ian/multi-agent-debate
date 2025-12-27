import type { AgentConfig, Message, AnalysisResult } from '$lib/types.ts';

const API_BASE = 'http://127.0.0.1:8000/api';

export interface SessionResponse {
	session_id: string;
	messages: Message[];
	error?: string;
}

export interface StreamingSessionResponse {
	session_id: string;
	error?: string;
}

export interface StreamMessage {
	agent: string;
	content: string;
	timestamp: number;
	status?: 'started' | 'completed';
	round?: number;
	error?: string;
}

export const startDebateSession = async (
	topic: string,
	agents: AgentConfig[]
): Promise<SessionResponse> => {
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

// Streaming API functions
export const createStreamingDebateSession = async (
	moderator_message: string,
	agents: AgentConfig[]
): Promise<StreamingSessionResponse> => {
	const response = await fetch(`${API_BASE}/create-streaming-debate-session`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ moderator_message, agents_config: agents })
	});
	if (!response.ok) throw new Error('Failed to start streaming session');
	return response.json();
};

export const initializeStreamingDebate = async (
	sessionId: string,
	moderator_message: string
): Promise<SessionResponse> => {
	const response = await fetch(`${API_BASE}/initialize-streaming-debate/${sessionId}`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ moderator_message })
	});
	if (!response.ok) throw new Error('Failed to initialize streaming debate');
	return response.json();
};

export function streamDebateRound(
	sessionId: string,
	onMessage: (message: Message | StreamMessage) => void,
	onComplete: () => void,
	onError: (error: string) => void
): () => void {
	const url = `${API_BASE}/stream-debate/${sessionId}`;

	const eventSource = new EventSource(url);

	eventSource.onmessage = (event) => {
		try {
			const data: StreamMessage = JSON.parse(event.data);

			if (data.status === 'started') {
				console.log('Debate round started:', data.round);
			} else if (data.status === 'completed') {
				onComplete();
				eventSource.close();
			} else if (data.error) {
				onError(data.error);
				eventSource.close();
			} else if (data.agent && data.content) {
				// Convert StreamMessage to Message format expected by the UI
				const message: Message = {
					agent: data.agent,
					content: data.content,
					round: data.round || 1,
					round_inner_index: 0 // Will be calculated by the UI
				};
				onMessage(message);
			}
		} catch (error) {
			onError(`Failed to parse message: ${error}`);
			eventSource.close();
		}
	};

	eventSource.onerror = (error) => {
		console.error('EventSource error:', error);
		onError('Connection lost');
		eventSource.close();
	};

	// Return cleanup function
	return () => {
		eventSource.close();
	};
}
