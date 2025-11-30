<script lang="ts">
    import { tick } from 'svelte';
    import type { AgentConfig, AgentName, DebateStatus, Message } from '$lib/types.ts';
    // Ensure saveDebate is imported
    import { startDebateSession, continueDebateSession, analyzeDebate, saveDebate } from '$lib/services/apiService.ts';
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

    // --- DERIVED STATE ---
    $: debaters = agents.filter(a => a.name.startsWith('Debater_'));
    $: isLoading = status === 'running'; 
    $: isIdle = status === 'idle';

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

    // --- MAIN LOGIC (AUTO-RUN) ---

    const processNewMessages = async (newMsgs: Message[]) => {
        for (const msg of newMsgs) {
            nextSpeaker = msg.agent;
            
            // Artificial typing delay
            const delay = Math.min(Math.max(msg.content.length * 5, 800), 2000);
            await new Promise(r => setTimeout(r, delay));

            messages = [...messages, msg];
            
            // Score Update
            if (msg.agent === 'Judge') {
                const match = msg.content.match(/Round Winner: (Debater_[A-Z])/i);
                if (match && scores[match[1]] !== undefined) {
                    scores[match[1]] += 1;
                }
            }
        }
        nextSpeaker = undefined;
    };

    const handleStartDebate = async () => {
        if (!topic.trim()) {
            error = "Please enter a debate topic.";
            return;
        }

        // 1. Capture User Topic (Fixes Zombie Topic Bug)
        const userTopic = topic;
        handleReset();
        topic = userTopic;

        status = 'running';
        // Moderator message immediate
        messages = [{ agent: 'Moderator', content: `Debate Topic: ${topic}`, round: 0 }];
        nextSpeaker = 'Debater_A'; // Guess first speaker for loader

        try {
            // 2. Start Live Session (Backend runs Round 1 only)
            const result = await startDebateSession(topic, agents);
            sessionId = result.session_id;
            
            // 3. Play out Round 1 messages
            round = 1;
            await processNewMessages(result.messages);
            
            // 4. TRIGGER THE AUTO LOOP
            await runAutoLoop();

        } catch (e: any) {
            console.error(e);
            error = `Backend Error: ${e.message}`;
            status = 'error';
            nextSpeaker = undefined;
        }
    };

    // Automatically runs rounds until MAX_ROUNDS is reached
    const runAutoLoop = async () => {
        while (round < MAX_ROUNDS && status === 'running') {
            if (!sessionId) break;

            // Small pause between rounds for visual clarity
            await new Promise(r => setTimeout(r, 1500));

            // Set visual indicator for next round
            nextSpeaker = 'Debater_A'; 

            // Trigger Backend for Next Round
            const result = await continueDebateSession(sessionId);
            
            // Increment round
            round++;

            // Play new messages
            await processNewMessages(result.messages);
        }

        // Finish, Analyze, and Save
        if (status !== 'error') {
            status = 'finished';
            calculateWinner();
            
            try {
                // Analyze
                analysisResult = await analyzeDebate(messages);
                
                // Save to Backend
                if (sessionId && analysisResult) {
                    console.log("Saving debate...");
                    await saveDebate(sessionId, analysisResult);
                    console.log("Debate saved successfully.");
                }
            } catch (err) { console.error("Analysis/Save failed", err); }
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
                        <button
                            on:click={handleStartDebate}
                            disabled={!isIdle}
                            class="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg transition duration-200"
                        >
                            {#if isLoading}
                                <div class="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
                                Running...
                            {:else}
                                <PlayIcon /> Start Auto-Debate
                            {/if}
                        </button>
                       
                        <button
                            on:click={handleReset}
                            disabled={isLoading}
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