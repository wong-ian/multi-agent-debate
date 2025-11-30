<script lang="ts">
    import type { AgentName } from '$lib/types.ts';
    import type { AnalysisResult } from '$lib/services/nlpService.ts';
    import ChartBarIcon from './icons/ChartBarIcon.svelte';
    import KeywordList from './KeywordList.svelte';

    export let analysisResult: AnalysisResult | null;
    export let debaters: AgentName[];

    let activeTab: 'summary' | 'timeline' = 'summary';

    // Type Narrowing Fix: Create a reactive variable that is guaranteed non-null if analysisResult is not null
    $: analysis = analysisResult ? analysisResult : null;
</script>

<div class="bg-gray-800/50 p-4 sm:p-6 rounded-lg border border-gray-700">
    <div class="flex items-center gap-3 mb-4">
        <ChartBarIcon />
        <h3 class="text-2xl font-bold text-indigo-300">Post-Debate Analysis</h3>
    </div>

    {#if !analysis}
        <h3 class="text-xl font-bold text-gray-400">Not enough data for analysis.</h3>
    {:else}
        <div class="border-b border-gray-600 mb-4">
            <nav class="flex space-x-4">
                <button
                    on:click={() => (activeTab = 'summary')}
                    class={`px-3 py-2 font-medium text-sm rounded-t-lg ${
                        activeTab === 'summary' ? 'bg-gray-700/80 text-white' : 'text-gray-400 hover:text-white'
                    }`}
                >
                    Summary
                </button>
                <button
                    on:click={() => (activeTab = 'timeline')}
                    class={`px-3 py-2 font-medium text-sm rounded-t-lg ${
                        activeTab === 'timeline' ? 'bg-gray-700/80 text-white' : 'text-gray-400 hover:text-white'
                    }`}
                >
                    Topic Timeline
                </button>
            </nav>
        </div>

        {#if activeTab === 'summary'}
            <div class="space-y-6">
                <KeywordList keywords={analysis.overallKeywords} title="Overall Top Keywords" />
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {#each debaters as name (name)}
                        <KeywordList
                            keywords={analysis.keywordsByDebater[name]}
                            title={`Top Keywords for ${name.replace('_', ' ')}`}
                            agentName={name}
                        />
                    {/each}
                </div>
            </div>
        {/if}

        {#if activeTab === 'timeline'}
            <div class="overflow-x-auto">
                <div class="flex space-x-4 p-2 min-w-max">
                    {#each analysis.timeline as { round, keywordsByDebater: roundKeywords } (round)}
                        <div class="bg-gray-900/50 p-4 rounded-lg w-72 shrink-0">
                            <h4 class="font-bold text-lg text-center text-gray-400 mb-4">Round {round}</h4>
                            <div class="space-y-4">
                                {#each debaters as name (name)}
                                    <KeywordList
                                        keywords={roundKeywords[name]}
                                        title={name.replace('_', ' ')}
                                        agentName={name}
                                    />
                                {/each}
                            </div>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}
    {/if}
</div>