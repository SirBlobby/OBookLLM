<script lang="ts">
	let { onCreate, onCancel } = $props();
	let newNotebookTitle = $state('');

	async function handleCreate() {
		if (!newNotebookTitle.trim()) return;
		await onCreate(newNotebookTitle);
		newNotebookTitle = '';
	}
</script>

<div
	class="mb-8 p-4 rounded-xl shadow-sm"
	style="background-color: var(--background-light); border: 1px solid var(--border);"
>
	<h3 class="font-semibold mb-3" style="color: var(--text);">Create New Notebook</h3>
	<div class="flex gap-2">
		<input
			type="text"
			bind:value={newNotebookTitle}
			placeholder="Notebook Title..."
			class="flex-1 px-4 py-2 rounded-lg focus:outline-none"
			style="background-color: var(--background); border: 1px solid var(--border); color: var(--text);"
			onkeydown={(e) => e.key === 'Enter' && handleCreate()}
		/>
		<button
			onclick={handleCreate}
			class="text-white px-4 py-2 rounded-lg"
			style="background-color: var(--primary);">Create</button
		>
		<button
			onclick={onCancel}
			class="px-4 py-2 rounded-lg"
			style="background-color: var(--surface); color: var(--text-muted);">Cancel</button
		>
	</div>
</div>
