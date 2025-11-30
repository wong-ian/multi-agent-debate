<script lang="ts">
	import type { Message } from '$lib/types.ts';
	import { getAgentUI } from '$lib/utils.ts';
	import BotIcon from './icons/BotIcon.svelte';

	export let message: Message;
	const ui = getAgentUI(message.agent);
</script>

<div class={`flex items-end gap-3 w-full ${ui.container}`}>
	{#if ui.isLeft}
		<div class="shrink-0">
			<BotIcon className={ui.icon} />
		</div>
	{/if}
	<div class={`max-w-3xl w-full p-4 rounded-xl ${ui.bubble} ${ui.rounded}`}>
		<p class="font-bold mb-1">{message.agent.replace('_', ' ')}</p>
		<p class="whitespace-pre-wrap text-gray-200">{message.content}</p>
	</div>
	{#if !ui.isLeft}
		<div class="shrink-0">
			<BotIcon className={ui.icon} />
		</div>
	{/if}
</div>