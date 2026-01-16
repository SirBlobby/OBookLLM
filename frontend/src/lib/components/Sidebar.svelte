<script lang="ts">
	import Icon from '@iconify/svelte';
	import { page } from '$app/stores';
	import { invalidateAll, goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { API_BASE_URL } from '$lib/api';

	let { session } = $props();

	import { notebooks, loading, fetchNotebooks } from '$lib/stores/notebooks';

	let isCollapsed = $state(false);

	onMount(() => {
		if ($notebooks.length === 0) {
			fetchNotebooks();
		}
	});

	function toggleSidebar() {
		isCollapsed = !isCollapsed;
	}

	async function handleSignOut() {
		try {
			await fetch('/api/auth/logout', { method: 'POST' });
			await invalidateAll();
			goto('/login');
		} catch (error) {
			console.error('Sign out error:', error);
			goto('/login');
		}
	}
</script>

<aside
	class="flex flex-col h-screen transition-all duration-300 {isCollapsed
		? 'w-20'
		: 'w-64'} relative z-50 shadow-xl"
	style="background-color: var(--background-light); border-right: 1px solid var(--border);"
>
	<!-- Header -->
	<div
		class="p-5 flex items-center {isCollapsed ? 'justify-center' : 'gap-4'} shrink-0 h-20"
		style="border-bottom: 1px solid var(--border);"
	>
		<div
			class="w-9 h-9 rounded flex items-center justify-center text-white shrink-0 shadow-sm shadow-primary/20 transition-transform active:scale-95"
			style="background-color: var(--primary);"
		>
			<Icon icon="mdi:notebook" width="22" />
		</div>
		{#if !isCollapsed}
			<span class="font-bold text-xl tracking-tight" style="color: var(--text);">OBookLLM</span>
		{/if}
	</div>

	<!-- Navigation -->
	<div class="flex-1 overflow-y-auto p-3 space-y-1 scrollbar-hide">
		{#if !isCollapsed}
			<div
				class="text-xs font-semibold uppercase tracking-wider mb-2 px-3 mt-2"
				style="color: var(--text-muted);"
			>
				Navigation
			</div>
		{/if}

		<a
			href="/"
			class="flex items-center {isCollapsed
				? 'justify-center'
				: 'gap-3'} px-4 py-2.5 rounded text-sm font-medium transition-all duration-200 group relative overflow-hidden"
			style="color: {$page.url.pathname === '/' ? 'white' : 'var(--text-muted)'};"
			title="Dashboard"
		>
			{#if $page.url.pathname === '/'}
				<div class="absolute inset-0 opacity-100" style="background-color: var(--primary);"></div>
			{:else}
				<div
					class="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-200"
					style="background-color: var(--text); opacity: 0.05;"
				></div>
			{/if}

			<div class="relative z-10 flex items-center gap-3">
				<Icon icon="mdi:view-dashboard" width="22" />
				{#if !isCollapsed}<span>Dashboard</span>{/if}
			</div>
		</a>

		<!-- Notebooks Section -->
		{#if !isCollapsed}
			<div
				class="text-xs font-semibold uppercase tracking-wider mt-6 mb-2 px-3"
				style="color: var(--text-muted);"
			>
				My Notebooks
			</div>
		{:else}
			<div class="my-3 border-t border-border opacity-40 mx-2"></div>
		{/if}

		{#if $loading && !isCollapsed}
			<div class="flex items-center gap-3 px-3 py-2 text-sm" style="color: var(--text-muted);">
				<Icon icon="mdi:loading" class="animate-spin" width="16" />
				<span>Loading...</span>
			</div>
		{:else if $notebooks.length === 0 && !isCollapsed}
			<div class="px-3 py-2 text-sm" style="color: var(--text-muted);">No notebooks yet</div>
		{:else}
			{#each $notebooks as notebook}
				{@const isActive = $page.url.pathname === `/notebook/${notebook.id}`}
				<a
					href="/notebook/{notebook.id}"
					class="flex items-center {isCollapsed
						? 'justify-center'
						: 'gap-3'} px-4 py-2.5 rounded text-sm font-medium transition-all duration-200 group relative"
					style="color: {isActive ? 'white' : 'var(--text-muted)'};"
					title={notebook.title}
				>
					{#if isActive}
						<div
							class="absolute inset-0 rounded shadow-sm shadow-primary/20"
							style="background-color: var(--primary);"
						></div>
					{/if}

					<div class="relative z-10 flex items-center gap-3 w-full">
						<Icon
							icon={notebook.status === 'processing' ? 'mdi:loading' : 'mdi:notebook-outline'}
							class="{notebook.status === 'processing'
								? 'animate-spin'
								: ''} shrink-0 transition-transform group-hover:scale-110"
							width="20"
						/>
						{#if !isCollapsed}
							<span class="truncate flex-1">{notebook.title}</span>
							{#if notebook.status === 'processing'}
								<span class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
							{/if}
						{/if}
					</div>
				</a>
			{/each}
		{/if}

		<!-- New Notebook Button -->
		<a
			href="/"
			class="flex items-center {isCollapsed
				? 'justify-center'
				: 'gap-3'} px-4 py-2.5 rounded text-sm transition-all duration-200 mt-4 group relative overflow-hidden border border-dashed"
			style="border-color: var(--border); color: var(--text-muted);"
			title="New Notebook"
		>
			<div
				class="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity"
			></div>
			<div class="relative z-10 flex items-center gap-2 group-hover:text-primary transition-colors">
				<Icon icon="mdi:plus" width="22" />
				{#if !isCollapsed}<span class="font-medium">New Notebook</span>{/if}
			</div>
		</a>
	</div>

	<!-- Footer -->
	<div class="p-3 space-y-1 shrink-0" style="border-top: 1px solid var(--border);">
		<!-- Collapse Toggle (Moved to Footer) -->
		<button
			type="button"
			onclick={toggleSidebar}
			class="flex items-center {isCollapsed
				? 'justify-center'
				: 'gap-3'} w-full px-3 py-2.5 rounded-lg transition-all duration-200 hover:bg-black/5 dark:hover:bg-white/5 mb-1"
			style="color: var(--text-muted);"
			title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
		>
			<Icon
				icon={isCollapsed ? 'mdi:chevron-double-right' : 'mdi:chevron-double-left'}
				width="20"
			/>
			{#if !isCollapsed}<span class="font-medium">Collapse</span>{/if}
		</button>

		<div class="w-full border-t border-border opacity-30 my-1"></div>

		{#if session?.user}
			<a
				href="/settings?tab=profile"
				class="flex items-center {isCollapsed
					? 'justify-center'
					: 'gap-3 px-3 py-2.5'} mb-2 rounded transition-colors hover:bg-black/5 dark:hover:bg-white/5 group"
				title="Profile & Settings"
			>
				<div
					class="w-8 h-8 rounded bg-primary flex items-center justify-center text-white font-bold text-xs shrink-0 uppercase"
				>
					{session.user.name?.[0] || session.user.email?.[0] || 'U'}
				</div>
				{#if !isCollapsed}
					<div class="flex-1 min-w-0 flex flex-col items-start leading-none gap-1">
						<span class="text-sm font-semibold truncate" style="color: var(--text);">
							{session.user.name || 'User'}
						</span>
						<span class="text-[10px] truncate opacity-60" style="color: var(--text-muted);">
							{session.user.email || 'No email'}
						</span>
					</div>
					<Icon
						icon="mdi:cog"
						width="16"
						class="opacity-0 group-hover:opacity-50 transition-opacity"
						style="color: var(--text-muted);"
					/>
				{/if}
			</a>
		{/if}

		{#if session}
			<button
				onclick={handleSignOut}
				class="flex items-center {isCollapsed
					? 'justify-center'
					: 'gap-3'} text-sm w-full px-3 py-2.5 rounded-lg transition-all duration-200 hover:bg-red-500/10 mt-1"
				style="color: var(--error);"
				title="Sign Out"
			>
				<Icon icon="mdi:logout" width="20" />
				{#if !isCollapsed}<span class="font-medium">Sign Out</span>{/if}
			</button>
		{:else}
			<a
				href="/login"
				class="flex items-center {isCollapsed
					? 'justify-center'
					: 'gap-3'} text-sm w-full px-3 py-2.5 rounded-lg transition-all duration-200 hover:bg-primary/10 mt-1"
				style="color: var(--primary);"
				title="Sign In"
			>
				<Icon icon="mdi:login" width="20" />
				{#if !isCollapsed}<span class="font-medium">Sign In</span>{/if}
			</a>
		{/if}
	</div>
</aside>
