<script lang="ts">
	import { getAgentUI } from '$lib/utils.ts';

	interface Props {
		topic: string;
		scores: Record<string, number>;
		round: number;
		winner?: string | 'Tie' | undefined;
	}

	let {
		topic,
		scores,
		round,
		winner = undefined
	}: Props = $props();

	let debaters = $derived(Object.keys(scores));
</script>

<div
	class="bg-gray-800/50 backdrop-blur-sm p-4 rounded-lg border border-gray-700 mb-4 sticky top-4 z-10"
>
	<h2 class="text-xl font-bold text-indigo-300 mb-2 truncate" title={topic}>
		Topic: <span class="text-gray-100 font-normal">{topic || 'Not set'}</span>
	</h2>
	<div class="flex flex-col gap-4 text-lg">
		<div class="flex gap-4 items-center flex-wrap">
			{#each debaters as debaterName (debaterName)}
				{@const ui = getAgentUI(debaterName)}
				<p class={ui.text}>
					{debaterName.replace('_', ' ')}:
					<span class="font-bold text-2xl">{scores[debaterName]}</span>
				</p>
			{/each}
		</div>
		<div>
			{#if winner}
				<p class="text-yellow-400 font-bold text-2xl animate-pulse">
					Winner: {winner.replace('_', ' ')}!
				</p>
			{:else}
				<p class="text-gray-400">
					Round: <span class="font-bold text-2xl">{round}</span>
				</p>
			{/if}
		</div>
	</div>
</div>