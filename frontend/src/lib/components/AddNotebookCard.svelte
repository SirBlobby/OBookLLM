<script lang="ts">
	import Icon from '@iconify/svelte';
	let { onClick } = $props();
</script>

<button
	onclick={onClick}
	class="group rounded-xl p-5 flex flex-col items-center justify-center gap-3 transition-all h-40"
	style="border: 2px dashed var(--border); color: var(--text-muted);"
>
	<div
		class="w-10 h-10 rounded-full flex items-center justify-center"
		style="background-color: var(--surface);"
	>
		<Icon icon="mdi:plus" width="24" />
	</div>
	<span class="font-medium">Create new notebook</span>
</button>
