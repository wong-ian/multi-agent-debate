<script lang="ts">
    import type { AgentConfig, AgentName, DebateStatus, Message } from '$lib/types.ts';
    import { startDebateSession, continueDebateSession, analyzeDebate } from '$lib/services/apiService.ts';
    import type { AnalysisResult } from '$lib/types.ts';
    
    // Components
    import AgentConfigurator from '$lib/components/AgentConfigurator.svelte';
    import DebateTranscript from '$lib/components/DebateTranscript.svelte';
    import Scoreboard from '$lib/components/Scoreboard.svelte';
    import DebateAnalysis from '$lib/components/DebateAnalysis.svelte';

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

    // --- NEW: MAST ANALYSIS STATE ---
    let roundAnalyses: Record<number, any> = {};

    // --- DERIVED STATE ---
    $: debaters = agents.filter(a => a.name.startsWith('Debater_'));
    $: isLoading = status === 'running'; 
    $: isIdle = status === 'idle';
    $: isPaused = status === 'paused';

    // --- HELPER FUNCTIONS ---
    
    const triggerMastAnalysis = async (roundNum: number, roundMsgs: Message[]) => {
        try {
            const res = await fetch('http://localhost:8000/api/mast-analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages: roundMsgs })
            });
            const result = await res.json();
            // Assign to new object to trigger Svelte reactivity
            roundAnalyses = { ...roundAnalyses, [roundNum]: result };
        } catch (e) {
            console.error("Shadow Judge analysis failed:", e);
        }
    };

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
        roundAnalyses = {}; // Reset MAST data
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

    const processNewMessages = async (newMsgs: Message[]) => {
        // 1. Visually type out each message in the round
        for (const msg of newMsgs) {
            nextSpeaker = msg.agent; // Update visual loader [cite: 3398]
            const delay = Math.min(Math.max(msg.content.length * 5, 1000), 3000);
            await new Promise(r => setTimeout(r, delay)); // Visual typing delay [cite: 3399]

            messages = [...messages, msg]; // Append message for display [cite: 3399]
            
            // Track scores if the Judge declared a winner [cite: 3400]
            if (msg.agent === 'Judge') {
                const match = msg.content.match(/Round Winner: (Debater_[A-Z])/i);
                if (match && scores[match[1]] !== undefined) {
                    scores[match[1]] += 1; // Update reactive scoreboard [cite: 3401]
                }
            }
        }
        
        nextSpeaker = undefined; // Clear loader after all messages are "typed" [cite: 3402]

        // 2. Trigger MAST failure mode analysis for the round just completed [cite: 3403]
        if (newMsgs.length > 0) {
            try {
                const res = await fetch('http://localhost:8000/api/analyze-taxonomy', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages: newMsgs }) // Send round trace for analysis [cite: 3404]
                });

                if (!res.ok) throw new Error(`Server responded with ${res.status}`);

                const result = await res.json();
                
                // Re-assigning the whole object with the new round result triggers Svelte's reactivity 
                roundAnalyses = { ...roundAnalyses, [round]: result };
            } catch (err) {
                console.error("Taxonomy analysis failed:", err);
            }
        }
    };

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
            status = 'paused';
        } catch (e: any) {
            error = `Backend Error: ${e.message}`;
            status = 'error';
            nextSpeaker = undefined;
        }
    };

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
                status = 'finished';
                calculateWinner();
                try {
                    analysisResult = await analyzeDebate(messages);
                } catch (err) { console.error("Analysis failed", err); }
            } else {
                status = 'paused';
            }
        } catch (e: any) {
            error = `Backend Error: ${e.message}`;
            status = 'error';
            nextSpeaker = undefined;
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
                            <button
                                on:click={handleNextRound}
                                class="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg transition duration-200 animate-pulse"
                            >
                                <ForwardIcon /> Next Round
                            </button>
                        {:else}
                            <button
                                on:click={handleStartDebate}
                                disabled={!isIdle}
                                class="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg transition duration-200"
                            >
                                {#if isLoading}
                                    <div class="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
                                    Thinking...
                                {:else}
                                    <PlayIcon /> Start
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
    </div>
</div>