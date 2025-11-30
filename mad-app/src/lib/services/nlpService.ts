import type { Message, AgentName } from '$lib/types.ts';

const STOP_WORDS = new Set([
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t', 'as', 'at',
    'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can\'t', 'cannot', 'could',
    'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing', 'don\'t', 'down', 'during', 'each', 'few', 'for',
    'from', 'further', 'had', 'hadn\'t', 'has', 'hasn\'t', 'have', 'haven\'t', 'having', 'he', 'he\'d', 'he\'ll', 'he\'s',
    'her', 'here', 'here\'s', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll', 'i\'m',
    'i\'ve', 'if', 'in', 'into', 'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s', 'me', 'more', 'most', 'mustn\'t',
    'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours',
    'ourselves', 'out', 'over', 'own', 'same', 'shan\'t', 'she', 'she\'d', 'she\'ll', 'she\'s', 'should', 'shouldn\'t',
    'so', 'some', 'such', 'than', 'that', 'that\'s', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there',
    'there\'s', 'these', 'they', 'they\'d', 'they\'ll', 'they\'re', 'they\'ve', 'this', 'those', 'through', 'to', 'too',
    'under', 'until', 'up', 'very', 'was', 'wasn\'t', 'we', 'we\'d', 'we\'ll', 'we\'re', 'we\'ve', 'were', 'weren\'t',
    'what', 'what\'s', 'when', 'when\'s', 'where', 'where\'s', 'which', 'while', 'who', 'who\'s', 'whom', 'why', 'why\'s',
    'with', 'won\'t', 'would', 'wouldn\'t', 'you', 'you\'d', 'you\'ll', 'you\'re', 'you\'ve', 'your', 'yours', 'yourself',
    'yourselves', 'debater_a', 'debater_b', 'debater_c', 'debater_d', 'judge', 'topic'
]);

const tokenize = (text: string): string[] => {
    if (!text) return [];
    return text
        .toLowerCase()
        .split(/[^a-z0-9]+/)
        .filter(word => word.length > 2 && !STOP_WORDS.has(word));
};

const computeTF = (term: string, tokenizedDoc: string[]): number => {
    const termCount = tokenizedDoc.filter(t => t === term).length;
    return termCount / tokenizedDoc.length;
};

const computeIDF = (term: string, tokenizedDocs: string[][]): number => {
    const docsWithTerm = tokenizedDocs.filter(doc => doc.includes(term)).length;
    return Math.log(tokenizedDocs.length / (docsWithTerm + 1));
};

const getTopKeywords = (docs: { id: string, content: string }[], corpus: string[], topN: number) => {
    const tokenizedCorpus = corpus.map(tokenize);
    const results: Record<string, { term: string, score: number }[]> = {};

    docs.forEach(doc => {
        const tokenizedDoc = tokenize(doc.content);
        const uniqueTerms = [...new Set(tokenizedDoc)];
        
        const tfidfScores = uniqueTerms.map(term => {
            const tf = computeTF(term, tokenizedDoc);
            const idf = computeIDF(term, tokenizedCorpus);
            return { term, score: tf * idf };
        });
        
        tfidfScores.sort((a, b) => b.score - a.score);
        results[doc.id] = tfidfScores.slice(0, topN);
    });

    return results;
};

export interface Keyword {
    term: string;
    score: number;
}

export interface AnalysisResult {
    overallKeywords: Keyword[];
    keywordsByDebater: Record<AgentName, Keyword[]>;
    timeline: {
        round: number;
        keywordsByDebater: Record<AgentName, Keyword[]>;
    }[];
}

export const analyzeDebate = (messages: Message[], debaterNames: AgentName[]): AnalysisResult | null => {
    const debaterMessages = messages.filter(m => m.agent.startsWith('Debater_'));
    if (debaterMessages.length === 0) return null;

    const rounds: Message[][] = [];
    let currentRoundMessages: Message[] = [];
    messages.forEach(msg => {
        if (msg.agent.startsWith('Debater_')) {
            currentRoundMessages.push(msg);
        }
        if (msg.agent === 'Judge' && currentRoundMessages.length > 0) {
            rounds.push(currentRoundMessages);
            currentRoundMessages = [];
        }
    });
    if (currentRoundMessages.length > 0) rounds.push(currentRoundMessages);

    const contentByDebater = debaterNames.reduce((acc, name) => {
        acc[name] = messages
            .filter(m => m.agent === name)
            .map(m => m.content)
            .join(' ');
        return acc;
    }, {} as Record<AgentName, string>);

    const overallContent = Object.values(contentByDebater).join(' ');
    const debaterCorpus = Object.values(contentByDebater);

    const overallKeywords = getTopKeywords([{ id: 'overall', content: overallContent }], debaterCorpus, 15)['overall'];

    const keywordsByDebater = getTopKeywords(
        debaterNames.map(name => ({ id: name, content: contentByDebater[name] })),
        debaterCorpus,
        10
    );

    const timeline = rounds.map((roundMessages, index) => {
        const roundCorpus = rounds.map(r => r.map(m => m.content).join(' '));
        const contentByDebaterInRound = debaterNames.reduce((acc, name) => {
            acc[name] = roundMessages
                .filter(m => m.agent === name)
                .map(m => m.content)
                .join(' ');
            return acc;
        }, {} as Record<AgentName, string>);
        
        const keywordsByDebaterInRound = getTopKeywords(
            debaterNames.map(name => ({ id: name, content: contentByDebaterInRound[name] })),
            roundCorpus,
            5
        );

        return {
            round: index + 1,
            keywordsByDebater: keywordsByDebaterInRound,
        };
    });

    return {
        overallKeywords,
        keywordsByDebater,
        timeline,
    };
};