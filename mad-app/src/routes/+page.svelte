<script lang="ts">
    import type { AgentConfig, AgentName, DebateStatus, Message, SpeakerMetadata } from '$lib/types.ts';
    // Note: Ensure apiService.ts exports startDebateSession and continueDebateSession
    import { startDebateSession, continueDebateSession, analyzeDebate } from '$lib/services/apiService.ts';
    import type { AnalysisResult } from '$lib/types.ts';
    import { getAgentUI } from '$lib/utils.ts';
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
    const MAX_ROUNDS = 5; // Controls when the debate finishes
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
    let topic = $state('AI will benefit society more than it will harm it.');
    let agents: AgentConfig[] = $state(JSON.parse(JSON.stringify(INITIAL_AGENTS)));
    
    // Live State
    let messages: Message[] = $state([]);
    let sessionId: string | null = null;
    let status: DebateStatus = $state('idle');
    let round = $state(0);
    let scores: Record<string, number> = $state({ Debater_A: 0, Debater_B: 0 });
    let winner: string | 'Tie' | undefined = $state(undefined);
    let error: string | null = $state(null);
    let analysisResult: AnalysisResult | null = $state(null);
    let nextSpeaker: AgentName | undefined = $state(undefined);
    let speaker_metadata: Record<AgentName, SpeakerMetadata> = $derived.by(() => {
        const metadata: Record<AgentName, SpeakerMetadata> = {};
        metadata['Moderator'] = {
            speaker_number: 0,
            color: '#9CA3AF' // Gray
        };
        agents.forEach((a, index) => {
            metadata[a.name] = {
                speaker_number: index+1,
                color: getAgentUI(a.name).colorHex
            }
        });
        return metadata;
    });
//     messages = [
//   {
//     "round": 1,
//     "round_inner_index": 0,
//     "agent": "Moderator",
//     "content": "Debate Topic: AI will benefit society more than it will harm it.",
//   },
//   {
//     "round": 1,
//     "round_inner_index": 1,
//     "agent": "Debater_A",
//     "content": "Absolutely, I believe that AI will benefit society more than it will harm it, and there are several compelling reasons for this.\n\nFirst and foremost, AI has the potential to revolutionize healthcare. Imagine being able to analyze vast amounts of medical data in an instant—AI can help diagnose diseases earlier and more accurately than ever before. For instance, it can identify patterns in imaging scans that the human eye might miss. This not only saves lives but also optimizes patient care and significantly reduces costs for healthcare systems.\n\nLet’s talk about efficiency too. In industries like manufacturing and logistics, AI-powered automation boosts productivity and reduces operational costs. By taking over repetitive and menial tasks, AI allows human workers to focus on more complex, creative, and fulfilling work. This isn't about replacing jobs; it's about enhancing human potential and creating new opportunities as industries evolve.\n\nNow, consider education. AI can personalize learning experiences, adapting to each student’s needs and pace. This enables a more effective and inclusive educational environment, reaching learners who might otherwise fall through the cracks. Everyone deserves access to quality education, and AI can help democratize this access on a global scale.\n\nMoreover, AI-driven advancements in sustainability cannot be overlooked. From optimizing energy usage to improving agricultural practices, AI tools are helping us address some of the most pressing challenges of our time—climate change and food security. These solutions not only benefit society but also foster a healthier planet for future generations.\n\nFinally, let's not ignore the potential for AI to enhance our daily lives. From smart assistants that simplify tasks to innovative applications improving our work-life balance, AI holds the promise of making life easier and more enjoyable.\n\nSure, there are risks and ethical considerations with AI, but that is true with any powerful technology. The focus should be on developing regulations and frameworks to ensure responsible use rather than shunning the technology altogether. By embracing AI and harnessing its capabilities, we can create a future that truly benefits society as a whole.\n\nSo, in conclusion, when we harness AI's potential responsibly, the benefits—enhanced healthcare, increased efficiency, personalized education, environmental sustainability, and improved quality of life—far outweigh the potential harms. The future is bright with AI, and it’s time we recognize that!",
//   },
//   {
//     "round": 1,
//     "round_inner_index": 2,
//     "agent": "Debater_B",
//     "content": "Thank you, Debater_A, but I respectfully disagree with your perspective on AI. While the benefits you've mentioned sound appealing, they often overlook some critical concerns that could lead to more harm than good for society.\n\nFirst, let's talk about healthcare. Yes, AI can analyze data quickly, but this raises significant questions about data privacy and security. Patients' sensitive medical information could become vulnerable to breaches, misuse, or even identity theft. Furthermore, an AI's misdiagnosis could lead to catastrophic consequences—it’s a massive responsibility to place solely in the hands of machines that lack human empathy and nuanced understanding.\n\nThen there’s the issue of job displacement. Sure, AI can free workers from repetitive tasks, but it also threatens the livelihoods of millions. Many industries are already experiencing this shift; workers are being replaced by machines, leading to unemployment and economic instability. The argument that AI will create new jobs doesn’t always hold water—often these new roles require skills that the displaced workers do not have, leaving them behind in an increasingly competitive job market.\n\nIn education, while personalization is beneficial, we must question the reliance on algorithms that might not fully understand a student's context or challenges. AI can exacerbate existing inequalities rather than remedy them, as access to advanced technology can be limited. Students from less privileged backgrounds might not have the same exposure to these educational tools, potentially widening the achievement gap.\n\nAs for environmental benefits, while AI is certainly being used to tackle sustainability issues, there's a flip side. The energy consumption required to run AI systems is substantial. The data centers that host AI tools consume vast amounts of electricity, contributing to the carbon footprint at a time when we should be reducing it, not increasing it.\n\nLastly, there’s the ethical dimension. Who is accountable when AI systems make errors or perpetuate biases? There are numerous cases where AI has reflected and amplified societal biases, leading to unfair treatment in areas like hiring or law enforcement. These are not just technical glitches; they're structural issues that highlight how flawed reliance on AI can shape our society in harmful ways.\n\nIn conclusion, while AI undoubtedly has the potential to contribute positively in some areas, the risks it poses to privacy, job security, equity in education, environmental sustainability, and ethical accountability cannot be ignored. Society needs to proceed with caution, ensuring safeguards and regulations are in place to mitigate these harms before fully integrating AI into critical areas of our lives. As much as the optimism sounds great, we must ask ourselves if we’re truly ready for the implications of widespread AI adoption."
//   },
//   {
//     "round": 1,
//     "round_inner_index": 3,
//     "agent": "Judge",
//     "content": "Both debaters presented strong arguments, but the effectiveness of their positions varied. Debater A laid out an optimistic and multifaceted view of AI's benefits, emphasizing healthcare, efficiency, education, sustainability, and enhanced daily life. However, they did not adequately address the potential drawbacks associated with AI, which are crucial to the debate.\n\nDebater B countered with significant concerns about privacy, job displacement, educational equity, environmental impact, and ethical accountability. Their arguments highlighted the complexities and risks involved in AI adoption, which are critical points that resonate with public sentiment and real-world implications.\n\nOverall, Debater B provided a more comprehensive analysis of the implications of AI technology, effectively countering Debater A's points by raising valid concerns and pressing for caution. \n\nRound Winner: Debater_B"
//   },
//   {
//     "round": 2,
//     "round_inner_index": 0,
//     "agent": "Debater_A",
//     "content": "Absolutely, I believe that AI will benefit society more than it will harm it, and there are several compelling reasons for this.\n\nFirst and foremost, AI has the potential to revolutionize healthcare. Imagine being able to analyze vast amounts of medical data in an instant—AI can help diagnose diseases earlier and more accurately than ever before. For instance, it can identify patterns in imaging scans that the human eye might miss. This not only saves lives but also optimizes patient care and significantly reduces costs for healthcare systems.\n\nLet’s talk about efficiency too. In industries like manufacturing and logistics, AI-powered automation boosts productivity and reduces operational costs. By taking over repetitive and menial tasks, AI allows human workers to focus on more complex, creative, and fulfilling work. This isn't about replacing jobs; it's about enhancing human potential and creating new opportunities as industries evolve.\n\nNow, consider education. AI can personalize learning experiences, adapting to each student’s needs and pace. This enables a more effective and inclusive educational environment, reaching learners who might otherwise fall through the cracks. Everyone deserves access to quality education, and AI can help democratize this access on a global scale.\n\nMoreover, AI-driven advancements in sustainability cannot be overlooked. From optimizing energy usage to improving agricultural practices, AI tools are helping us address some of the most pressing challenges of our time—climate change and food security. These solutions not only benefit society but also foster a healthier planet for future generations.\n\nFinally, let's not ignore the potential for AI to enhance our daily lives. From smart assistants that simplify tasks to innovative applications improving our work-life balance, AI holds the promise of making life easier and more enjoyable.\n\nSure, there are risks and ethical considerations with AI, but that is true with any powerful technology. The focus should be on developing regulations and frameworks to ensure responsible use rather than shunning the technology altogether. By embracing AI and harnessing its capabilities, we can create a future that truly benefits society as a whole.\n\nSo, in conclusion, when we harness AI's potential responsibly, the benefits—enhanced healthcare, increased efficiency, personalized education, environmental sustainability, and improved quality of life—far outweigh the potential harms. The future is bright with AI, and it’s time we recognize that!",
//   },
//   {
//     "round": 2,
//     "round_inner_index": 1,
//     "agent": "Debater_B",
//     "content": "Thank you, Debater_A, but I respectfully disagree with your perspective on AI. While the benefits you've mentioned sound appealing, they often overlook some critical concerns that could lead to more harm than good for society.\n\nFirst, let's talk about healthcare. Yes, AI can analyze data quickly, but this raises significant questions about data privacy and security. Patients' sensitive medical information could become vulnerable to breaches, misuse, or even identity theft. Furthermore, an AI's misdiagnosis could lead to catastrophic consequences—it’s a massive responsibility to place solely in the hands of machines that lack human empathy and nuanced understanding.\n\nThen there’s the issue of job displacement. Sure, AI can free workers from repetitive tasks, but it also threatens the livelihoods of millions. Many industries are already experiencing this shift; workers are being replaced by machines, leading to unemployment and economic instability. The argument that AI will create new jobs doesn’t always hold water—often these new roles require skills that the displaced workers do not have, leaving them behind in an increasingly competitive job market.\n\nIn education, while personalization is beneficial, we must question the reliance on algorithms that might not fully understand a student's context or challenges. AI can exacerbate existing inequalities rather than remedy them, as access to advanced technology can be limited. Students from less privileged backgrounds might not have the same exposure to these educational tools, potentially widening the achievement gap.\n\nAs for environmental benefits, while AI is certainly being used to tackle sustainability issues, there's a flip side. The energy consumption required to run AI systems is substantial. The data centers that host AI tools consume vast amounts of electricity, contributing to the carbon footprint at a time when we should be reducing it, not increasing it.\n\nLastly, there’s the ethical dimension. Who is accountable when AI systems make errors or perpetuate biases? There are numerous cases where AI has reflected and amplified societal biases, leading to unfair treatment in areas like hiring or law enforcement. These are not just technical glitches; they're structural issues that highlight how flawed reliance on AI can shape our society in harmful ways.\n\nIn conclusion, while AI undoubtedly has the potential to contribute positively in some areas, the risks it poses to privacy, job security, equity in education, environmental sustainability, and ethical accountability cannot be ignored. Society needs to proceed with caution, ensuring safeguards and regulations are in place to mitigate these harms before fully integrating AI into critical areas of our lives. As much as the optimism sounds great, we must ask ourselves if we’re truly ready for the implications of widespread AI adoption."
//   },
//   {
//     "round": 2,
//     "round_inner_index": 2,
//     "agent": "Judge",
//     "content": "Both debaters presented strong arguments, but the effectiveness of their positions varied. Debater A laid out an optimistic and multifaceted view of AI's benefits, emphasizing healthcare, efficiency, education, sustainability, and enhanced daily life. However, they did not adequately address the potential drawbacks associated with AI, which are crucial to the debate.\n\nDebater B countered with significant concerns about privacy, job displacement, educational equity, environmental impact, and ethical accountability. Their arguments highlighted the complexities and risks involved in AI adoption, which are critical points that resonate with public sentiment and real-world implications.\n\nOverall, Debater B provided a more comprehensive analysis of the implications of AI technology, effectively countering Debater A's points by raising valid concerns and pressing for caution. \n\nRound Winner: Debater_B"
//   }
// ]
    // --- DERIVED STATE ---
    let debaters = $derived(agents.filter(a => a.name.startsWith('Debater_')));
    let isLoading = $derived((status as DebateStatus) === 'running'); 
    let isIdle = $derived((status as DebateStatus) === 'idle');
    let isPaused = $derived((status as DebateStatus) === 'paused'); // Used to show "Next Round" button

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

    // --- MAIN LOGIC ---

    // Takes a list of new messages from the backend and "types" them out visually
    const processNewMessages = async (newMsgs: Message[]) => {
        for (const msg of newMsgs) {
            // Set visual indicator
            nextSpeaker = msg.agent;

            // Visual delay based on length
            // const delay = Math.min(Math.max(msg.content.length * 5, 1000), 3000);
            // await new Promise(r => setTimeout(r, delay));

            // Add message to display
            messages = [...messages, msg];
            
            // Score tracking
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
        messages = [{ agent: 'Moderator', content: `Debate Topic: ${topic}`, round: 1, round_inner_index: 0 }];
        nextSpeaker = 'Debater_A'; // Guess first speaker for loader

        try {
            // 2. Start Live Session (Backend runs Round 1 only)
            const result = await startDebateSession(topic, agents);
            console.log({result});
            sessionId = result.session_id;
            
            // 3. Play out Round 1 messages
            round = 1;
            await processNewMessages(result.messages);
            
            // 4. Pause and wait for user input
            status = 'paused';

        } catch (e: any) {
            console.error(e);
            error = `Backend Error: ${e.message}`;
            status = 'error';
            nextSpeaker = undefined;
        }
    };

    const handleNextRound = async () => {
        if (!sessionId) return;
        status = 'running';
        
        // Visual indicator (guess next speaker based on last)
        const lastSpeaker = messages[messages.length - 1]?.agent;
        nextSpeaker = lastSpeaker === 'Judge' ? 'Debater_A' : 'Judge'; 

        try {
            // 1. Trigger Backend for Next Round
            const result = await continueDebateSession(sessionId);
            
            // 2. Increment Round Counter visually
            round++;
            
            // 3. Play out new messages
            await processNewMessages(result.messages);
            
            // 4. Check End Condition
            if (round >= MAX_ROUNDS) {
                status = 'finished';
                calculateWinner();
                // Fetch Analysis
                try {
                    analysisResult = await analyzeDebate(messages);
                } catch (err) { console.error("Analysis failed", err); }
            } else {
                status = 'paused';
            }
        } catch (e: any) {
            console.error(e);
            error = `Backend Error: ${e.message}`;
            status = 'error';
            nextSpeaker = undefined;
        }
    };
</script>

<svelte:head>
    <title>AI Debate Arena</title>
</svelte:head>

<div class="h-screen bg-gray-900 text-gray-100 font-sans p-4 sm:p-6 lg:p-8 flex flex-col">
    <div class="max-w-8xl grow flex flex-col">
        <!-- <header class="text-center mb-8">
            <h1 class="text-4xl sm:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500">
                AI Debate Arena
            </h1>
            <p class="text-gray-400 mt-2">Powered by AutoGen & Python Backend</p>
        </header> -->

        <main class="flex flex-col gap-6 grow">
            <!-- Row 1: Controllers and Scoreboard -->
            <section class="flex flex-col gap-6">
                <!-- Controllers Column -->
                <div class="flex gap-6">
                    <div class="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                        <label for="topic" class="block text-lg font-semibold text-indigo-300 mb-2">Debate Topic</label>
                        <textarea
                            id="topic"
                            bind:value={topic}
                            disabled={!isIdle}
                            class="w-[25rem] h-24 bg-gray-900/80 p-2 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 transition duration-200"
                            placeholder="e.g., Is pineapple on pizza a culinary masterpiece?"
                        ></textarea>
                        
                        <div class="mt-4 flex space-x-4">
                            {#if isPaused}
                                <button
                                    onclick={handleNextRound}
                                    class="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg transition duration-200 animate-pulse"
                                >
                                    <ForwardIcon /> Next Round
                                </button>
                            {:else}
                                <button
                                    onclick={handleStartDebate}
                                    disabled={!isIdle}
                                    class="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white  py-2 px-4 rounded-lg transition duration-200"
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
                                onclick={handleReset}
                                disabled={isLoading && !isPaused}
                                class="w-full flex items-center justify-center gap-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white py-2 px-4 rounded-lg transition duration-200"
                            >
                                <RefreshIcon /> Reset
                            </button>
                        </div>
                        {#if error}
                            <p class="text-red-400 mt-2 text-sm">{error}</p>
                        {/if}
                    </div>

                    <div class="flex gap-4">
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
                            onclick={handleAddDebater}
                            disabled={!isIdle}
                            class="w-full flex items-center justify-center gap-2 border-2 border-dashed border-gray-600 hover:border-indigo-500 hover:text-indigo-400 text-gray-400 font-bold py-2 px-4 rounded-lg transition duration-200 disabled:cursor-not-allowed disabled:border-gray-700 disabled:text-gray-600"
                        >
                            <PlusCircleIcon /> Add Debater
                        </button>
                    </div>
                </div>

                <!-- Scoreboard Column -->
                <div class="lg:col-span-1">
                    <Scoreboard {topic} {scores} {round} {winner} />
                </div>
            </section>

            <!-- Row 2: Debate Transcript -->
            <section class="grow flex flex-col">
                <DebateTranscript 
                    {messages} 
                    {isLoading} 
                    {nextSpeaker}
                    speaker_metadata={speaker_metadata}
                    currentRound={round}
                />
            </section>

            <!-- Row 3: Debate Analysis -->
            {#if status === 'finished' && analysisResult}
                <section>
                    <DebateAnalysis {analysisResult} debaters={debaters.map(d => d.name)} />
                </section>
            {/if}
        </main>
    </div>
</div>