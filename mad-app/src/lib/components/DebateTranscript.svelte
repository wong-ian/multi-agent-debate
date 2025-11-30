<script lang="ts">
    import { afterUpdate, beforeUpdate } from 'svelte';
    import type { Message, AgentName } from '$lib/types.ts';
    import { getAgentUI } from '$lib/utils.ts';
    import BotIcon from './icons/BotIcon.svelte';
    import ChevronDown from './icons/ChevronDownIcon.svelte';
    import ChevronUp from './icons/ChevronUpIcon.svelte';

    export let messages: Message[];
    export let isLoading: boolean;
    export let nextSpeaker: AgentName | undefined = undefined;
    export let currentRound: number;

    let scrollContainer: HTMLDivElement;
    let shouldAutoScroll = false;
    // Track which rounds are open
    let openRounds: Record<number, boolean> = {};

    // Group messages by round
    $: groupedMessages = messages.reduce((acc, msg) => {
        const r = msg.round || 1;
        if (!acc[r]) acc[r] = [];
        acc[r].push(msg);
        return acc;
    }, {} as Record<number, Message[]>);

    $: roundNumbers = (() => {
        const rounds = new Set(Object.keys(groupedMessages).map(Number));
        if (currentRound > 0) rounds.add(currentRound);
        return Array.from(rounds).sort((a, b) => a - b);
    })();

    // --- FIX 1: AUTO-OPEN CURRENT ROUND ---
    // Whenever currentRound changes, ensure it is set to open in the dictionary
    $: {
        if (currentRound > 0) {
            openRounds[currentRound] = true;
        }
    }

    // Scroll Logic
    beforeUpdate(() => {
        if (scrollContainer) {
            const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
            shouldAutoScroll = scrollHeight - scrollTop <= clientHeight + 50;
        }
    });

    afterUpdate(() => {
        if (shouldAutoScroll && scrollContainer) {
            scrollContainer.scrollTo({ top: scrollContainer.scrollHeight, behavior: 'smooth' });
        }
    });

    const toggleRound = (r: number) => {
        // Svelte reactivity quirk: assign to a new object or trigger update
        openRounds[r] = !openRounds[r]; 
    };
</script>

<div class="h-full flex flex-col bg-gray-900/70 p-4 rounded-lg border border-gray-700">
    <div class="flex-grow overflow-y-auto pr-2 custom-scrollbar" bind:this={scrollContainer}>
        {#each roundNumbers as r}
            {@const msgs = groupedMessages[r] || []}
            {@const isCurrentRound = r === currentRound}
            {@const showLoader = isCurrentRound && isLoading && nextSpeaker}
            
            <div class="mb-4 bg-gray-800/30 rounded-lg border border-gray-700/50 overflow-hidden">
                <button
                    on:click={() => toggleRound(r)}
                    class="w-full flex justify-between items-center p-3 bg-gray-800/80 hover:bg-gray-700/80 transition-colors text-left"
                >
                    <span class="font-bold text-gray-300">Round {r}</span>
                    {#if openRounds[r]}<ChevronUp />{:else}<ChevronDown />{/if}
                </button>
       
                {#if openRounds[r]}
                    <div class="p-4 space-y-6">
                        {#each msgs as message}
                            {@const ui = getAgentUI(message.agent)}
                            <div class="flex items-end gap-3 w-full {ui.container}">
                                {#if ui.isLeft}<BotIcon className="{ui.icon} flex-shrink-0" />{/if}
                                <div class="max-w-3xl w-full p-4 rounded-xl {ui.bubble} {ui.rounded}">
                                    <p class="font-bold mb-1">{message.agent.replace('_', ' ')}</p>
                                    <p class="whitespace-pre-wrap text-gray-200">{message.content}</p>
                                </div>
                                {#if !ui.isLeft}<BotIcon className="{ui.icon} flex-shrink-0" />{/if}
                            </div>
                        {/each}

                        {#if showLoader && nextSpeaker}
                            {@const nextUI = getAgentUI(nextSpeaker)}
                            <div class="flex items-end gap-3 w-full {nextUI.container}">
                                {#if nextUI.isLeft}<BotIcon className="{nextUI.icon} flex-shrink-0" />{/if}
                                <div class="max-w-xs w-full p-4 rounded-xl bg-gray-700/50 flex items-center space-x-2">
                                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
                                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style="animation-delay: 0.2s"></div>
                                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style="animation-delay: 0.4s"></div>
                                </div>
                                {#if !nextUI.isLeft}<BotIcon className="{nextUI.icon} flex-shrink-0" />{/if}
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/each}
    </div>
</div>