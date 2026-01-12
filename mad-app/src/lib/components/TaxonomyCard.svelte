<script lang="ts">
    export let analysis: {
        failures: Array<{ mode_id: string; mode_name: string; reasoning: string }>;
        health_score: number;
        summary: string;
    };
</script>

<div class="mt-4 p-4 rounded-lg border border-indigo-500/30 bg-indigo-900/10">
    <div class="flex justify-between items-center mb-2">
        <h4 class="text-indigo-300 font-bold flex items-center gap-2">
            <span class="text-xs px-2 py-0.5 rounded bg-indigo-500 text-white">MAST ANALYSIS</span>
            Round Health: {analysis.health_score}%
        </h4>
    </div>
    
    <p class="text-sm text-gray-300 italic mb-3">"{analysis.summary}"</p>

    {#if analysis.failures.length > 0}
        <div class="space-y-2">
            {#each analysis.failures as failure}
                <div class="text-xs p-2 rounded bg-red-900/20 border border-red-500/30">
                    <span class="font-bold text-red-400">{failure.mode_id} ({failure.mode_name}):</span>
                    <span class="text-gray-200 ml-1">{failure.reasoning}</span>
                </div>
            {/each}
        </div>
    {:else}
        <div class="text-xs text-green-400 font-semibold">✓ No MAS failure modes detected.</div>
    {/if}
</div>