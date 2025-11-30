<script lang="ts">
    import type { AgentConfig, AgentName } from '$lib/types.ts';
    import { getAgentUI } from '$lib/utils.ts';
    import TrashIcon from './icons/TrashIcon.svelte';
    import { createEventDispatcher } from 'svelte';

    export let agent: AgentConfig;
    export let isRemovable: boolean = false;
    export let disabled: boolean;

    const dispatch = createEventDispatcher<{
        configChange: { name: AgentName; newConfig: string };
        remove: AgentName;
    }>();

    const ui = getAgentUI(agent.name);

    function handleConfigChange(event: Event) {
        // Use HTMLTextAreaElement directly in the event handler to get target value
        const target = event.target as HTMLTextAreaElement;
        dispatch('configChange', { name: agent.name, newConfig: target.value });
    }

    function handleRemove() {
        dispatch('remove', agent.name);
    }
</script>

<div class={`p-4 rounded-lg border relative ${ui.border} ${ui.bg}`}>
    {#if isRemovable}
        <button
            on:click={handleRemove}
            {disabled}
            class="absolute top-2 right-2 text-gray-400 hover:text-red-400 disabled:text-gray-600 disabled:cursor-not-allowed transition-colors"
            aria-label={`Remove ${agent.name}`}
        >
            <TrashIcon />
        </button>
    {/if}
    <h3 class={`font-bold text-lg mb-2 ${ui.text}`}>{agent.name.replace('_', ' ')}</h3>
    
    <textarea
        value={agent.systemMessage}
        on:input={handleConfigChange}
        {disabled}
        class="w-full h-48 bg-gray-900/80 text-gray-200 p-2 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 transition duration-200 text-sm"
        placeholder={`Enter system message for ${agent.name}`}
    ></textarea>
</div>