<script lang="ts">
    export let analysis: {
        summary: string;
        task_progress: string;
        failures: Array<{ id: string; name: string; detected: boolean }>;
    };

    $: detectedFailures = analysis.failures.filter(f => f.detected);
</script>

<div class="mt-6 p-4 rounded-xl border border-indigo-500/30 bg-indigo-900/10">
    <div class="flex items-center justify-between mb-3">
        <h4 class="text-indigo-300 font-bold uppercase text-xs tracking-widest">MAST Round Health Check</h4>
        <span class={`px-2 py-0.5 rounded text-[10px] font-bold ${analysis.task_progress === 'yes' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            PROGRESS: {analysis.task_progress.toUpperCase()}
        </span>
    </div>
    
    <p class="text-sm text-gray-300 italic mb-4">"{analysis.summary}"</p>

    <div class="flex flex-wrap gap-2">
        {#each detectedFailures as failure}
            <div class="text-[10px] px-2 py-1 rounded bg-red-900/30 border border-red-500/30 text-red-300">
                <span class="font-black">FM-{failure.id}:</span> {failure.name}
            </div>
        {:else}
            <div class="text-[10px] text-green-400 font-semibold italic">✓ No system failure modes detected this round.</div>
        {/each}
    </div>
</div>