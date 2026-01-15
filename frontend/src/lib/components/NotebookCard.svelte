<script lang="ts">
	import Icon from '@iconify/svelte';

	let { notebook } = $props();
</script>

<a
	href="/notebook/{notebook.id}"
	class="group p-5 rounded-xl shadow-sm hover:shadow-md transition-all flex flex-col h-40 justify-between"
	style="background-color: var(--background-light); border: 1px solid var(--border);"
>
	<div class="flex items-start justify-between">
		<div class="p-2 rounded-lg text-white" style="background-color: var(--primary);">
			<Icon icon="mdi:notebook" width="24" />
		</div>
		<button class="p-1" style="color: var(--text-muted);">
			<Icon icon="mdi:dots-vertical" width="20" />
		</button>
	</div>
	<div>
		<h3 class="font-semibold" style="color: var(--text);">{notebook.title}</h3>
		<div class="text-xs mt-1 flex items-center gap-2" style="color: var(--text-muted);">
			<span>{notebook.source_count || 0} sources</span>
			<span class="w-1 h-1 rounded-full" style="background-color: var(--border);"></span>
			<span>{notebook.updated || 'Just now'}</span>
		</div>
	</div>
</a>
