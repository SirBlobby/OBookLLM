<script lang="ts">
	import '../../app.css';
	let { children } = $props();
</script>

<div class="min-h-screen overflow-y-auto" style="background-color: var(--background); color: var(--text);">
	{@render children()}
</div>
