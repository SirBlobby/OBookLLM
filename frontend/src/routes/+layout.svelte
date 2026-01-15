<script lang="ts">
	import '../app.css';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import { page } from '$app/stores';

	let { children } = $props();
	let session = $derived($page.data.session);
</script>

<div
	class="flex h-screen w-full transition-colors"
	style="background-color: var(--background); color: var(--text);"
>
	<Sidebar {session} />

	<!-- Main Content -->
	<main
		class="flex-1 overflow-hidden flex flex-col relative w-full"
		style="background-color: var(--background);"
	>
		{@render children()}
	</main>
</div>
