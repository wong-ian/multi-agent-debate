export type AgentName = string;
export type DebateStatus = 'idle' | 'running' | 'paused' | 'error' | 'finished';

export interface SpeakerMetadata {
	speaker_number: number;
	// get color from agent UI
	color: string;
}
export interface Message {
	agent: AgentName;
	content: string;
	round: number;
	round_inner_index?: number;
}

export interface AgentConfig {
	name: AgentName;
	systemMessage: string;
}

// Matches the return dictionary from debate_logic.py -> run_debate()
export interface DebateResult {
	topic: string;
	winner: string;
	round_victories: Record<string, number>;
	message_count: number;
	messages: Message[];
}

export interface Keyword {
	term: string;
	score: number;
}

// Matches the return dictionary from nlp_logic.py -> perform_analysis()
export interface AnalysisResult {
	overallKeywords: Keyword[];
	keywordsByDebater: Record<AgentName, Keyword[]>;
	timeline: {
		round: number;
		keywordsByDebater: Record<AgentName, Keyword[]>;
	}[];
}
