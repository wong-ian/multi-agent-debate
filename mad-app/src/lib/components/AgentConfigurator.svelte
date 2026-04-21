<script lang="ts">
    import type { AgentConfig, AgentName } from '$lib/types.ts';
    import { getAgentUI } from '$lib/utils.ts';
    import TrashIcon from './icons/TrashIcon.svelte';
    import { createEventDispatcher } from 'svelte';
    import { PERSONAS, getPersonaMessage, type PersonaId } from '$lib/personas.ts';

    export let agent: AgentConfig;
    export let isRemovable: boolean = false;
    export let disabled: boolean;
    export let compact: boolean = false;

    const dispatch = createEventDispatcher<{
        configChange: { name: AgentName; newConfig: string };
        remove: AgentName;
    }>();

    const ui = getAgentUI(agent.name);

    let selectedPersona: PersonaId = 'default';
    $: isDebater = agent.name.startsWith('Debater_');
    $: currentPersonaDescription = PERSONAS.find(p => p.id === selectedPersona)?.description ?? '';

    function handleConfigChange(event: Event) {
        const target = event.target as HTMLTextAreaElement;
        dispatch('configChange', { name: agent.name, newConfig: target.value });
    }

    function handlePersonaChange(event: Event) {
        const select = event.target as HTMLSelectElement;
        selectedPersona = select.value as PersonaId;
        const newMessage = getPersonaMessage(agent.name, selectedPersona);
        dispatch('configChange', { name: agent.name, newConfig: newMessage });
    }

    function handleRemove() {
        dispatch('remove', agent.name);
    }
</script>

<div class={`p-4 rounded-lg border relative h-full ${ui.border} ${ui.bg}`}>
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

    {#if isDebater}
        <div class="mb-2">
            <label for={`persona-${agent.name}`} class="block text-xs text-gray-400 font-semibold mb-1 uppercase tracking-wide">Persona</label>
            <select
                id={`persona-${agent.name}`}
                value={selectedPersona}
                on:change={handlePersonaChange}
                {disabled}
                class="w-full bg-gray-900/80 text-gray-200 border border-gray-600 rounded-md px-2 py-1.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
                {#each PERSONAS as persona}
                    <option value={persona.id}>{persona.label}</option>
                {/each}
            </select>
            {#if selectedPersona !== 'default'}
                <p class="text-xs text-gray-500 mt-1 italic">{currentPersonaDescription}</p>
            {/if}
        </div>
    {/if}

    <textarea
        value={agent.systemMessage}
        on:input={handleConfigChange}
        {disabled}
        class={`w-full ${compact ? 'h-28' : 'h-48'} bg-gray-900/80 text-gray-200 p-2 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 transition duration-200 text-sm`}
        placeholder={`Enter system message for ${agent.name}`}
    ></textarea>
</div>
