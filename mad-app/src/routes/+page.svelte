<script lang="ts">
    import { tick } from 'svelte';
    import type { AgentConfig, AgentName, DebateStatus, Message } from '$lib/types.ts';
    // IMPORTS: Added saveDebate for data persistence
    import { startDebateSession, continueDebateSession, analyzeDebate, saveDebate, regenerateRound } from '$lib/services/apiService.ts';
    import type { AnalysisResult } from '$lib/types.ts';
    
    // Components
    import AgentConfigurator from '$lib/components/AgentConfigurator.svelte';
    import DebateTranscript from '$lib/components/DebateTranscript.svelte';
    import Scoreboard from '$lib/components/Scoreboard.svelte';
    import DebateAnalysis from '$lib/components/DebateAnalysis.svelte';
    import DebateVisualization from '$lib/components/DebateVisualization.svelte';

    // NLP service for per-round keyword extraction
    import { analyzeDebate as nlpAnalyze } from '$lib/services/nlpService.ts';
    import type { Keyword } from '$lib/types.ts';

    // Icons
    import PlayIcon from '$lib/components/icons/PlayIcon.svelte';
    import RefreshIcon from '$lib/components/icons/RefreshIcon.svelte';
    import PlusCircleIcon from '$lib/components/icons/PlusCircleIcon.svelte';
    import ForwardIcon from '$lib/components/icons/ForwardIcon.svelte';

    // --- CONFIGURATION ---
    const MAX_ROUNDS = 5;
    const BASE_JUDGE_MESSAGE = `You are a neutral debate judge.
Your job is to provide a brief critique of the arguments you just heard and declare a winner for that round.
Style: Be direct, impartial, and concise. Do not use formal salutations.
Your response MUST end with one of these exact phrases:`;

    const INITIAL_AGENTS: AgentConfig[] = [
        {
            name: 'Debater_A',
            systemMessage: `You are Debater_A. Your goal is to argue **FOR** the topic.\nStyle: Be direct, confident, and conversational.`
        },
        {
            name: 'Debater_B',
            systemMessage: `You are Debater_B. Your goal is to argue **AGAINST** the topic.\nStyle: Be direct, confident, and conversational.`
        },
        {
            name: 'Judge',
            systemMessage: `${BASE_JUDGE_MESSAGE}\nRound Winner: Debater_A\nRound Winner: Debater_B`
        }
    ];

    // --- STATE ---
    let topic = 'AI will benefit society more than it will harm it.';
    let agents: AgentConfig[] = JSON.parse(JSON.stringify(INITIAL_AGENTS));
    
    // Live State
    let messages: Message[] = [];
    let sessionId: string | null = null;
    let status: DebateStatus = 'idle';
    let round = 0;
    let scores: Record<string, number> = { Debater_A: 0, Debater_B: 0 };
    let winner: string | 'Tie' | undefined = undefined;
    let error: string | null = null;
    let analysisResult: AnalysisResult | null = null;
    let nextSpeaker: AgentName | undefined = undefined;

    // --- MAST ANALYSIS STATE ---
    let roundAnalyses: Record<number, any> = {};

    // --- PER-ROUND KEYWORD STATE ---
    let roundKeywords: Record<number, Keyword[]> = {};

    // --- HUMAN MODERATOR INTERVENTION STATE ---
    let regeneratedRounds: Record<number, { mastFailures: string[]; humanInput: string }> = {};
    let showIntervention = false;
    let interventionInput = '';
    let isRegenerating = false;

    // --- DERIVED STATE ---
    $: debaters = agents.filter(a => a.name.startsWith('Debater_'));
    $: isLoading = status === 'running'; 
    $: isIdle = status === 'idle';
    $: isPaused = status === 'paused';

    // --- HELPER FUNCTIONS ---
    
    const updateJudgeSystemMessage = (currentAgents: AgentConfig[]) => {
        const currentDebaters = currentAgents.filter(a => a.name.startsWith('Debater_'));
        const winnerOptions = currentDebaters.map(d => `Round Winner: ${d.name}`).join('\n');
        const newSystemMessage = `${BASE_JUDGE_MESSAGE}\n${winnerOptions}`;
        return currentAgents.map(a => a.name === 'Judge' ? { ...a, systemMessage: newSystemMessage } : a);
    };

    const handleAddDebater = () => {
        const nextLetter = String.fromCharCode('A'.charCodeAt(0) + debaters.length);
        const newDebaterName = `Debater_${nextLetter}` as AgentName;
        const newDebater: AgentConfig = {
            name: newDebaterName,
            systemMessage: `You are ${newDebaterName}. Argue your assigned position.`
        };
        const currentDebaters = agents.filter(a => a.name !== 'Judge');
        const judge = agents.find(a => a.name === 'Judge');
        if (judge) {
            agents = updateJudgeSystemMessage([...currentDebaters, newDebater, judge]);
        }
    };

    const handleRemoveDebater = (name: AgentName) => {
        agents = updateJudgeSystemMessage(agents.filter(a => a.name !== name));
    };

    const handleConfigChange = (e: CustomEvent) => {
        const { name, newConfig } = e.detail;
        agents = agents.map(a => a.name === name ? { ...a, systemMessage: newConfig } : a);
    };

    const handleReset = () => {
        status = 'idle';
        messages = [];
        sessionId = null;
        topic = 'AI will benefit society more than it will harm it.';
        agents = JSON.parse(JSON.stringify(INITIAL_AGENTS));
        round = 0;
        scores = { Debater_A: 0, Debater_B: 0 };
        winner = undefined;
        error = null;
        analysisResult = null;
        nextSpeaker = undefined;
        roundAnalyses = {};
        roundKeywords = {};
        regeneratedRounds = {};
        showIntervention = false;
        interventionInput = '';
        isRegenerating = false;
    };

    const calculateWinner = () => {
        const entries = Object.entries(scores);
        if (entries.length === 0) {
            winner = 'Tie';
            return;
        }
        entries.sort((a, b) => b[1] - a[1]);
        if (entries.length > 1 && entries[0][1] === entries[1][1]) {
            winner = 'Tie';
        } else {
            winner = entries[0][0];
        }
    };

    const recalculateScores = () => {
        const newScores: Record<string, number> = {};
        debaters.forEach(d => { newScores[d.name] = 0; });
        messages.forEach(msg => {
            if (msg.agent === 'Judge') {
                const match = msg.content.match(/Round Winner: (Debater_[A-Z])/i);
                if (match && newScores[match[1]] !== undefined) {
                    newScores[match[1]] += 1;
                }
            }
        });
        scores = newScores;
    };

    const handleIntervene = async () => {
        if (!sessionId) return;
        isRegenerating = true;
        error = null;

        const currentRoundAnalysis = roundAnalyses[round];
        const mastFailures: string[] = currentRoundAnalysis?.failures
            ?.filter((f: any) => f.detected)
            ?.map((f: any) => `${f.id}: ${f.name}`) || [];
        const roundToReplace = round;

        try {
            const result = await regenerateRound(sessionId, roundToReplace, mastFailures, interventionInput);

            // Replace round messages — keep everything except the replaced round
            const kept = messages.filter(m => m.round !== roundToReplace);
            messages = [...kept, ...result.messages];

            // Track for memory cell visualization
            regeneratedRounds = {
                ...regeneratedRounds,
                [roundToReplace]: { mastFailures, humanInput: interventionInput }
            };

            // Clear stale analysis/keywords for this round
            const { [roundToReplace]: _ra, ...restAnalyses } = roundAnalyses;
            roundAnalyses = restAnalyses;
            const { [roundToReplace]: _rk, ...restKeywords } = roundKeywords;
            roundKeywords = restKeywords;

            // Recalculate scores from full transcript
            recalculateScores();

            // Re-run MAST analysis on updated messages
            try {
                const res = await fetch('http://localhost:8000/api/analyze-taxonomy', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages })
                });
                if (res.ok) {
                    const mastResult = await res.json();
                    roundAnalyses = { ...roundAnalyses, [roundToReplace]: mastResult };
                }
            } catch { /* non-fatal */ }

            // Re-run NLP keywords for this round
            const nlpResult = nlpAnalyze(messages, debaters.map(d => d.name));
            if (nlpResult) {
                const roundData = nlpResult.timeline.find(t => t.round === roundToReplace);
                if (roundData) {
                    const all = Object.values(roundData.keywordsByDebater)
                        .flat()
                        .sort((a: any, b: any) => b.score - a.score);
                    const seen = new Set<string>();
                    const top5 = (all as any[]).filter((k: any) => !seen.has(k.term) && seen.add(k.term)).slice(0, 5);
                    roundKeywords = { ...roundKeywords, [roundToReplace]: top5 };
                }
            }

            showIntervention = false;
            interventionInput = '';
        } catch (e: any) {
            error = `Regeneration failed: ${e.message}`;
        } finally {
            isRegenerating = false;
        }
    };

    // --- CORE LOGIC ---

    // Handles typing effects AND triggers MAST analysis per round
    const processNewMessages = async (newMsgs: Message[]) => {
        // 1. Visually type out each message in the round
        for (const msg of newMsgs) {
            nextSpeaker = msg.agent; 
            const delay = Math.min(Math.max(msg.content.length * 5, 1000), 3000);
            await new Promise(r => setTimeout(r, delay)); 

            messages = [...messages, msg]; 
            
            // Track scores if the Judge declared a winner
            if (msg.agent === 'Judge') {
                const match = msg.content.match(/Round Winner: (Debater_[A-Z])/i);
                if (match && scores[match[1]] !== undefined) {
                    scores[match[1]] += 1; 
                }
            }
        }
        
        nextSpeaker = undefined; 

        // 2. Trigger MAST failure mode analysis for the round just completed
        if (newMsgs.length > 0) {
            try {
                const res = await fetch('http://localhost:8000/api/analyze-taxonomy', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages: messages })
                });

                if (!res.ok) throw new Error(`Server responded with ${res.status}`);

                const result = await res.json();
                
                // Re-assigning triggers Svelte's reactivity for the Taxonomy Card
                roundAnalyses = { ...roundAnalyses, [round]: result };
            } catch (err) {
                console.error("Taxonomy analysis failed:", err);
            }

            // 3. Compute per-round keywords client-side via TF-IDF
            const nlpResult = nlpAnalyze(messages, debaters.map(d => d.name));
            if (nlpResult) {
                const roundData = nlpResult.timeline.find(t => t.round === round);
                if (roundData) {
                    const all = Object.values(roundData.keywordsByDebater)
                        .flat()
                        .sort((a, b) => b.score - a.score);
                    const seen = new Set<string>();
                    const top5 = all.filter(k => !seen.has(k.term) && seen.add(k.term)).slice(0, 5);
                    roundKeywords = { ...roundKeywords, [round]: top5 };
                }
            }
        }
    };

    // Initializes the debate but PAUSES after Round 1 so user can choose mode
    const handleStartDebate = async () => {
        if (!topic.trim()) {
            error = "Please enter a debate topic.";
            return;
        }
        const userTopic = topic;
        handleReset();
        topic = userTopic;
        status = 'running';
        messages = [{ agent: 'Moderator', content: `Debate Topic: ${topic}`, round: 0 }];
        nextSpeaker = 'Debater_A';

        try {
            const result = await startDebateSession(topic, agents);
            sessionId = result.session_id;
            round = 1;
            await processNewMessages(result.messages);
            status = 'paused'; // Pauses here to allow Manual vs Auto choice
        } catch (e: any) {
            error = `Backend Error: ${e.message}`;
            status = 'error';
            nextSpeaker = undefined;
        }
    };

    // MANUAL MODE: Steps forward one round then pauses
    const handleNextRound = async () => {
        if (!sessionId) return;
        status = 'running';
        const lastSpeaker = messages[messages.length - 1]?.agent;
        nextSpeaker = lastSpeaker === 'Judge' ? 'Debater_A' : 'Judge'; 

        try {
            const result = await continueDebateSession(sessionId);
            round++;
            await processNewMessages(result.messages);
            
            if (round >= MAX_ROUNDS) {
                await finishDebate();
            } else {
                status = 'paused';
            }
        } catch (e: any) {
            error = `Backend Error: ${e.message}`;
            status = 'error';
            nextSpeaker = undefined;
        }
    };

    // AUTO MODE: Runs continuously until done
    const runAutoLoop = async () => {
        status = 'running'; 
        while (round < MAX_ROUNDS && status === 'running') {
            if (!sessionId) break;
            
            // Visual pause between rounds
            await new Promise(r => setTimeout(r, 1500));
            
            const lastSpeaker = messages[messages.length - 1]?.agent;
            nextSpeaker = lastSpeaker === 'Judge' ? 'Debater_A' : 'Judge'; 

            const result = await continueDebateSession(sessionId);
            round++;
            await processNewMessages(result.messages);
        }

        if (status !== 'error') {
            await finishDebate();
        }
    };

    // SHARED FINISH LOGIC: Calculates winner, Analyzes, and SAVES
    const finishDebate = async () => {
        status = 'finished';
        calculateWinner();
        try {
            // 1. Get the High-Level Summary (Keywords, etc.)
            let fullAnalysis = await analyzeDebate(messages);

            // 2. INJECT MAST DATA: Add the detailed per-round logs we collected
            if (fullAnalysis) {
                (fullAnalysis as any).mast_breakdown = roundAnalyses; 
            }

            analysisResult = fullAnalysis;

            // 3. Auto-Save to Backend
            if (sessionId && analysisResult) {
                console.log("Saving debate with full logs...");
                await saveDebate(sessionId, analysisResult);
            }
        } catch (err) { console.error("Analysis/Save failed", err);
        }
    };
</script>

<svelte:head>
    <title>AI Debate Arena</title>
</svelte:head>

<div class="min-h-screen bg-gray-900 text-gray-100 font-sans p-4 sm:p-6 lg:p-8">
    <div class="max-w-8xl mx-auto">
        <header class="text-center mb-8">
            <h1 class="text-4xl sm:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500">
                AI Debate Arena
            </h1>
            <p class="text-gray-400 mt-2">Powered by AutoGen & Python Backend</p>
        </header>

        <main class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <aside class="lg:col-span-1 flex flex-col gap-6">
                <div class="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                    <label for="topic" class="block text-lg font-semibold text-indigo-300 mb-2">Debate Topic</label>
                    <textarea
                        id="topic"
                        bind:value={topic}
                        disabled={!isIdle}
                        class="w-full h-24 bg-gray-900/80 p-2 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 transition duration-200"
                        placeholder="e.g., Is pineapple on pizza a culinary masterpiece?"
                    ></textarea>
                    
                    <div class="mt-4 flex space-x-4">
                        {#if isPaused}
                            <div class="flex gap-2 w-full">
                                <button
                                    on:click={handleNextRound}
                                    class="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg transition duration-200"
                                >
                                    <ForwardIcon /> Next
                                </button>
                                <button
                                    on:click={runAutoLoop}
                                    class="flex-1 flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-lg transition duration-200 animate-pulse"
                                >
                                    <PlayIcon /> Auto
                                </button>
                            </div>
                        {:else}
                            <button
                                on:click={handleStartDebate}
                                disabled={!isIdle}
                                class="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg transition duration-200"
                            >
                                {#if isLoading}
                                    <div class="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
                                    Running...
                                {:else}
                                    <PlayIcon /> Start Debate
                                {/if}
                            </button>
                        {/if}
                       
                        <button
                            on:click={handleReset}
                            disabled={isLoading && !isPaused}
                            class="w-full flex items-center justify-center gap-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg transition duration-200"
                        >
                            <RefreshIcon /> Reset
                        </button>
                    </div>
                    {#if isPaused && round > 0}
                        <div class="mt-3">
                            {#if !showIntervention}
                                <button
                                    on:click={() => showIntervention = true}
                                    class="w-full flex items-center justify-center gap-2 border border-amber-600 hover:bg-amber-900/30 text-amber-400 font-semibold py-2 px-4 rounded-lg transition duration-200 text-sm"
                                >
                                    ⚡ Intervene on Round {round}
                                </button>
                            {:else}
                                <div class="bg-gray-900/80 border border-amber-700/60 rounded-lg p-3 space-y-3">
                                    <div class="flex items-center justify-between">
                                        <span class="text-amber-400 font-bold text-sm">⚡ Human Moderator — Round {round}</span>
                                        <button on:click={() => { showIntervention = false; interventionInput = ''; }} class="text-gray-500 hover:text-gray-300 text-xs">✕ cancel</button>
                                    </div>

                                    {#if roundAnalyses[round]?.failures?.filter((f: any) => f.detected).length > 0}
                                        <div>
                                            <p class="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-1">MAST Failures Detected:</p>
                                            <div class="space-y-1">
                                                {#each roundAnalyses[round].failures.filter((f: any) => f.detected) as failure}
                                                    <div class="flex items-center gap-2 text-xs bg-red-900/30 border border-red-800/40 rounded px-2 py-1">
                                                        <span class="font-black text-red-400">{failure.id}</span>
                                                        <span class="text-red-200">{failure.name}</span>
                                                    </div>
                                                {/each}
                                            </div>
                                        </div>
                                    {:else}
                                        <p class="text-xs text-green-400 italic">No MAST failures in this round.</p>
                                    {/if}

                                    <div>
                                        <label for="intervention-input" class="text-xs text-gray-400 font-semibold uppercase tracking-wide block mb-1">Your direction for Round {round}:</label>
                                        <textarea
                                            id="intervention-input"
                                            bind:value={interventionInput}
                                            class="w-full h-20 bg-gray-800 p-2 border border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 transition resize-none"
                                            placeholder="e.g., Focus on concrete evidence, avoid logical fallacies..."
                                        ></textarea>
                                    </div>

                                    <button
                                        on:click={handleIntervene}
                                        disabled={isRegenerating}
                                        class="w-full flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg transition duration-200 text-sm"
                                    >
                                        {#if isRegenerating}
                                            <div class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                                            Regenerating...
                                        {:else}
                                            ⚡ Regenerate Round {round}
                                        {/if}
                                    </button>
                                </div>
                            {/if}
                        </div>
                    {/if}

                    {#if error}
                        <p class="text-red-400 mt-2 text-sm">{error}</p>
                    {/if}
                </div>

                <div class="space-y-4">
                    {#each agents as agent (agent.name)}
                        <AgentConfigurator 
                            {agent} 
                            on:configChange={handleConfigChange} 
                            on:remove={(e) => handleRemoveDebater(e.detail)}
                            isRemovable={agent.name.startsWith('Debater_') && debaters.length > 2}
                            disabled={!isIdle} 
                        />
                    {/each}
                    <button
                        on:click={handleAddDebater}
                        disabled={!isIdle}
                        class="w-full flex items-center justify-center gap-2 border-2 border-dashed border-gray-600 hover:border-indigo-500 hover:text-indigo-400 text-gray-400 font-bold py-2 px-4 rounded-lg transition duration-200 disabled:cursor-not-allowed disabled:border-gray-700 disabled:text-gray-600"
                    >
                        <PlusCircleIcon /> Add Debater
                    </button>
                </div>
            </aside>

            <section class="lg:col-span-2 h-[80vh] flex flex-col gap-4">
                <Scoreboard {topic} {scores} {round} {winner} />
                <DebateTranscript 
                    {messages} 
                    {isLoading} 
                    {nextSpeaker}
                    currentRound={round}
                    {roundAnalyses} 
                />
            </section>
        </main>
        
        {#if status === 'finished' && analysisResult}
            <section class="mt-8">
                <DebateAnalysis {analysisResult} debaters={debaters.map(d => d.name)} />
            </section>
        {/if}

        {#if messages.length > 1}
            <section class="mt-12 pt-8 border-t border-gray-700/50">
                <DebateVisualization {messages} {roundAnalyses} {roundKeywords} {regeneratedRounds} />
            </section>
        {/if}
    </div>
</div>