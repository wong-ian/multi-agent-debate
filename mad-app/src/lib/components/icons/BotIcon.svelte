<script>
    // Note: The prop name 'className' is common practice, but Svelte prefers 'class' 
    // for styling, so we default the prop to an empty string.
    export let className = ''; 
</script>

<svg 
    xmlns="http://www.w3.org/2000/svg" 
    class="h-8 w-8 {className}" 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    stroke-width="2" 
    stroke-linecap="round" 
    stroke-linejoin="round"
    {...$$props}
>
    <path d="M12 8V4H8" />
    <rect x="4" y="12" width="16" height="8" rx="2" />
    <path d="M2 12h2" />
    <path d="M20 12h2" />
    <path d="M12 18v-2" />
    <path d="M12 12V8" />
</svg>