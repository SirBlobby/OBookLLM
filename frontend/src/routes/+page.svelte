<script lang="ts">
	import Icon from '@iconify/svelte';
	import { onMount } from 'svelte';
	import NotebookCard from '$lib/components/NotebookCard.svelte';
	import CreateNotebookPanel from '$lib/components/CreateNotebookPanel.svelte';
	import AddNotebookCard from '$lib/components/AddNotebookCard.svelte';
	import { PUBLIC_BACKEND_URL } from '$env/static/public';

	let isCreating = $state(false);
	import { notebooks, fetchNotebooks } from '$lib/stores/notebooks';

	async function handleCreateNotebook(title: string) {
		try {
			const res = await fetch(`${PUBLIC_BACKEND_URL}/notebooks/create`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ title })
			});
			if (res.ok) {
				await fetchNotebooks();
				isCreating = false;
			}
		} catch (e) {
			console.error('Failed to create notebook', e);
		}
	}

	onMount(() => {
		if ($notebooks.length === 0) fetchNotebooks();
	});
</script>

<div class="p-8 max-w-5xl mx-auto w-full">
	<header class="flex items-center justify-between mb-8">
		<div>
			<h1 class="text-2xl font-bold" style="color: var(--text);">Welcome back</h1>
			<p style="color: var(--text-muted);">
				Select a notebook to start chatting or create a new one.
			</p>
		</div>
		<button
			onclick={() => (isCreating = true)}
			class="px-4 py-2 rounded-lg flex items-center gap-2 font-medium transition-colors text-white"
			style="background-color: var(--primary);"
		>
			<Icon icon="mdi:plus" width="20" />
			New Notebook
		</button>
	</header>

	{#if isCreating}
		<CreateNotebookPanel onCreate={handleCreateNotebook} onCancel={() => (isCreating = false)} />
	{/if}

	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
		{#each $notebooks as notebook}
			<NotebookCard {notebook} />
		{/each}

		<AddNotebookCard onClick={() => (isCreating = true)} />
	</div>
</div>
