<!-- @migration-task Error while migrating Svelte code: Can't migrate code with afterUpdate and beforeUpdate. Please migrate by hand. -->
<script lang="ts">
    import type { Message, AgentName } from '$lib/types.ts';
    import { getAgentUI } from '$lib/utils.ts';
    import BotIcon from './icons/BotIcon.svelte';
    import ChevronDown from './icons/ChevronDownIcon.svelte';
    import ChevronUp from './icons/ChevronUpIcon.svelte';
    import { MessageRenderer } from '$lib/components/MessageRenderer.ts';

    type GroupedMessages = {
        [round: number]: {
            [agent in AgentName]: Message[];
        }
    }

    let { messages, isLoading, nextSpeaker = undefined, speaker_metadata }: {
        messages: Message[];
        speaker_metadata: Record<AgentName, any>;
        isLoading: boolean;
        nextSpeaker?: AgentName | undefined;
    } = $props();

    let messageRenderers: Record<AgentName, MessageRenderer> = {};
    let scrollContainer: HTMLDivElement;
    let shouldAutoScroll = false;
    // Track which rounds are open
    let openRounds: Record<number, boolean> = {};

    // let speaker_metadata = $derived.by(() => {
    //     const metadata: Record<AgentName, any> = {};
    //     let speaker_count = 0;
    //     messages.forEach(msg => {
    //         if(!metadata[msg.agent]) {
    //             metadata[msg.agent] = {
    //                 messageCount: 0,
    //                 speaker_number: speaker_count,
    //                 // get color from agent UI
    //                 color: getAgentUI(msg.agent).colorHex
    //             };
    //             speaker_count += 1;
    //         }
    //         metadata[msg.agent].messageCount += 1;
    //     });
    //     console.log('Speaker metadata:', metadata);
    //     return metadata;
    // })
    // Group messages by round
    let groupedMessages: GroupedMessages = $derived.by(() => {
        const grouped: GroupedMessages = {};
        messages.forEach(msg => {
            const r = msg.round;
            if (!grouped[r]) grouped[r] = {};
            if (!grouped[r][msg.agent]) grouped[r][msg.agent] = [];
            grouped[r][msg.agent].push(msg);
        });
        console.log('Grouped Messages:', grouped);
        return grouped;
    })

    let roundNumbers = $derived.by(() => {
        const rounds = new Set(Object.keys(groupedMessages).map(Number));
        return Array.from(rounds).sort((a, b) => a - b);
    })

    $effect(() => {
        console.log('Updating Message Renderers', messageRenderers);
        const speaker_num = Object.keys(speaker_metadata).length;
        Object.entries(groupedMessages).forEach(([round, speaker_msgs]) => {
            Object.entries(speaker_msgs).forEach(([speaker, msgs]) => {
                console.log('Updating renderer for', speaker, 'in round', round);
                const node_id = `speaker-${speaker}-${round}`;
                if(messageRenderers[node_id]) {
                    messageRenderers[node_id].update(msgs, speaker_num, speaker_metadata[speaker]);
                }
            })
        })
    })

    // Scroll Logic
    // beforeUpdate(() => {
    //     if (scrollContainer) {
    //         const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
    //         shouldAutoScroll = scrollHeight - scrollTop <= clientHeight + 50;
    //     }
    // });

    // afterUpdate(() => {
    //     if (shouldAutoScroll && scrollContainer) {
    //         scrollContainer.scrollTo({ top: scrollContainer.scrollHeight, behavior: 'smooth' });
    //     }
    // });

    const toggleRound = (r: number) => {
        // Svelte reactivity quirk: assign to a new object or trigger update
        openRounds[r] = !openRounds[r]; 
    };

    function handleSvgMounted(node: SVGSVGElement) {
        // This function can be used to manipulate the SVG element after it's mounted
        // For example, you could add event listeners or modify attributes here
        const speaker = node.id.split('-')[1] as AgentName;
        const round = parseInt(node.id.split('-')[2]);
        const bbox = node.getBoundingClientRect();
        if (!messageRenderers[node.id]) {
            messageRenderers[node.id] = new MessageRenderer(node.id, bbox.width, bbox.height, handleMessageClicked);
        }
        const speaker_num = Object.keys(speaker_metadata).length;
        messageRenderers[node.id].update(groupedMessages[round]?.[speaker] || [], speaker_num, speaker_metadata[speaker]);
    }

    function handleMessageClicked(event: any, message: Message) {
        console.log('Message clicked:', message);
        // Implement any additional logic for when a message is clicked
    }
</script>

<div class="bg-[#333333] self-stretch grow flex divide relative">
    {#each roundNumbers as r}
        {@const speaker_messages = groupedMessages[r] || []}
        <div class="round-container flex flex-col grow divide-y">
            {#each Object.keys(speaker_metadata) as speaker}
                {@const messages = speaker_messages[speaker] || []}
                <div class="speaker-row flex flex-col flex-1 p-2 ">
                    <div class="font-bold">
                        {speaker}
                    </div>
                    <svg id={`speaker-${speaker}-${r}`} class="h-0 grow" use:handleSvgMounted></svg>
                </div>
            {/each}
        </div>
        {#if r < Math.max(...roundNumbers)}
        <div class="round-separator w-2 my-2 mx-1">
            <svg class="w-full h-full" viewBox="0 0 10 100" preserveAspectRatio="none">
                <line class="" x1="5" y1="0" x2="5" y2="100" stroke="#888888" stroke-width="3" stroke-dasharray="1 2" />
            </svg>
        </div>
        {/if}
    {/each}

</div>
<!-- <div class="h-full flex flex-col bg-gray-900/70 p-4 rounded-lg border border-gray-700">
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
</div> -->