<script lang="ts">
	import type { AgentName } from '$lib/types.ts';
	import type { Keyword } from '$lib/services/nlpService.ts';
	import { getAgentUI } from '$lib/utils.ts';

	interface Props {
		keywords: Keyword[];
		title: string;
		agentName?: AgentName | undefined;
	}

	let { keywords, title, agentName = undefined }: Props = $props();

	let ui = $derived(agentName ? getAgentUI(agentName) : null);
</script>

<div>
	<h4 class={`font-bold mb-2 ${ui ? ui.text : 'text-indigo-300'}`}>{title}</h4>
	{#if keywords && keywords.length > 0}
		<ul class="flex flex-wrap gap-2">
			{#each keywords as { term } (term)}
				<li class="bg-gray-700 text-gray-200 text-sm px-2 py-1 rounded-md">
					{term}
				</li>
			{/each}
		</ul>
	{:else}
		<p class="text-gray-500 italic text-sm">No significant keywords found.</p>
	{/if}
</div>