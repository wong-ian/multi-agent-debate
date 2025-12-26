<!-- @migration-task Error while migrating Svelte code: $$props is used together with named props in a way that cannot be automatically migrated. -->
<script>
    export let className = 'h-6 w-6';
</script>

<svg 
    xmlns="http://www.w3.org/2000/svg" 
    class="{className}" 
    fill="none" 
    viewBox="0 0 24 24" 
    stroke="currentColor" 
    {...$$props}
>
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
</svg>