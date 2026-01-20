<script lang="ts">
	import Icon from '@iconify/svelte';
	import { API_BASE_URL } from '$lib/api';
	import { goto } from '$app/navigation';
	import { fetchNotebooks } from '$lib/stores/notebooks';

	interface Props {
		isOpen: boolean;
		notebookId: string;
		currentTitle: string;
		initialTab?: 'settings' | 'share';
		onClose: () => void;
		onRename: (newTitle: string) => void;
		onClearHistory?: () => Promise<void>;
	}

	let {
		isOpen,
		notebookId,
		currentTitle,
		initialTab = 'settings',
		onClose,
		onRename,
		onClearHistory
	}: Props = $props();

	// svelte-ignore state_referenced_locally
	let title = $state(currentTitle);
	let loading = $state(false);
	let deleteConfirm = $state(false);
	let clearHistoryConfirm = $state(false);
	let clearingHistory = $state(false);
	let activeTab = $state<'settings' | 'share'>('settings');
	let copied = $state(false);

	$effect(() => {
		if (isOpen) {
			title = currentTitle;
			deleteConfirm = false;
			clearHistoryConfirm = false;
			activeTab = initialTab;
			copied = false;
		}
	});

	async function handleRename() {
		if (!title.trim() || title === currentTitle) return;
		loading = true;
		try {
			const res = await fetch(`${API_BASE_URL}/notebooks/${notebookId}/rename`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ title: title.trim() })
			});
			if (res.ok) {
				await fetchNotebooks();
				onRename(title.trim());
				onClose();
			}
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	}

	async function handleDelete() {
		loading = true;
		try {
			const res = await fetch(`${API_BASE_URL}/notebooks/${notebookId}`, {
				method: 'DELETE'
			});
			if (res.ok) {
				await fetchNotebooks();
				goto('/');
			}
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	}

	function copyLink() {
		navigator.clipboard.writeText(window.location.href);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}

	async function handleClearHistory() {
		if (!onClearHistory) return;
		clearingHistory = true;
		try {
			await onClearHistory();
			clearHistoryConfirm = false;
			onClose();
		} catch (e) {
			console.error(e);
		} finally {
			clearingHistory = false;
		}
	}
</script>

{#if isOpen}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4"
		style="background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px);"
		onclick={(e) => e.target === e.currentTarget && onClose()}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
		onkeydown={(e) => e.key === 'Escape' && onClose()}
	>
		<div
			class="w-full max-w-md rounded-2xl shadow-2xl overflow-hidden flex flex-col"
			style="background-color: var(--background-light); border: 1px solid var(--border);"
		>
			<!-- Header -->
			<div class="px-6 pt-6 pb-2">
				<h2 class="text-xl font-semibold" style="color: var(--text);">Notebook Options</h2>
			</div>

			<!-- Tabs -->
			<div class="flex px-6 border-b border-gray-700/50" style="border-color: var(--border);">
				<button
					onclick={() => (activeTab = 'share')}
					class="pb-2 px-1 mr-4 text-sm font-medium transition-colors border-b-2"
					style={activeTab === 'share'
						? 'color: var(--primary); border-color: var(--primary);'
						: 'color: var(--text-muted); border-color: transparent;'}
				>
					Share
				</button>
				<button
					onclick={() => (activeTab = 'settings')}
					class="pb-2 px-1 text-sm font-medium transition-colors border-b-2"
					style={activeTab === 'settings'
						? 'color: var(--primary); border-color: var(--primary);'
						: 'color: var(--text-muted); border-color: transparent;'}
				>
					Settings
				</button>
			</div>

			<!-- Content -->
			<div class="p-6 space-y-6">
				{#if activeTab === 'share'}
					<div class="space-y-4">
						<p class="text-sm" style="color: var(--text-muted);">
							Anyone with the link can view this notebook.
						</p>

						<div class="flex items-center gap-2">
							<div
								class="flex-1 px-4 py-2 rounded-lg text-sm truncate"
								style="background-color: var(--background); border: 1px solid var(--border); color: var(--text-muted);"
							>
								{window.location.href}
							</div>
							<button
								onclick={copyLink}
								class="px-4 py-2 rounded-lg text-sm font-medium transition-colors text-white whitespace-nowrap"
								style="background-color: {copied ? 'var(--success)' : 'var(--primary)'}"
							>
								{copied ? 'Copied' : 'Copy Link'}
							</button>
						</div>
					</div>
				{:else}
					<!-- Rename Section -->
					<div class="space-y-2">
						<label
							for="notebook-title"
							class="text-sm font-medium"
							style="color: var(--text-muted);"
						>
							Notebook Name
						</label>
						<input
							id="notebook-title"
							type="text"
							bind:value={title}
							class="w-full px-4 py-2 rounded-lg focus:outline-none focus:ring-2"
							style="background-color: var(--background); border: 1px solid var(--border); color: var(--text); --tw-ring-color: var(--primary);"
						/>
					</div>

					<div class="flex gap-2">
						<button
							onclick={handleRename}
							disabled={loading || !title.trim() || title === currentTitle}
							class="flex-1 py-2 rounded-lg text-sm font-medium text-white transition-opacity disabled:opacity-50"
							style="background-color: var(--primary);"
						>
							{loading ? 'Saving...' : 'Save Changes'}
						</button>
					</div>

					<div class="h-px w-full" style="background-color: var(--border);"></div>

					<!-- Clear History Section -->
					<div>
						{#if !clearHistoryConfirm}
							<button
								onclick={() => (clearHistoryConfirm = true)}
								class="w-full py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
								style="color: var(--warning); border: 1px solid var(--warning);"
							>
								<Icon icon="mdi:chat-remove" width="18" />
								Clear Chat History
							</button>
						{:else}
							<div class="space-y-3">
								<p class="text-sm text-center" style="color: var(--text);">
									Clear all messages? This cannot be undone.
								</p>
								<div class="flex gap-2">
									<button
										onclick={() => (clearHistoryConfirm = false)}
										class="flex-1 py-2 rounded-lg text-sm font-medium"
										style="background-color: var(--background); color: var(--text);"
									>
										Cancel
									</button>
									<button
										onclick={handleClearHistory}
										disabled={clearingHistory}
										class="flex-1 py-2 rounded-lg text-sm font-medium text-white"
										style="background-color: var(--warning);"
									>
										{clearingHistory ? 'Clearing...' : 'Confirm Clear'}
									</button>
								</div>
							</div>
						{/if}
					</div>

					<div class="h-px w-full" style="background-color: var(--border);"></div>

					<!-- Delete Section -->
					<div>
						{#if !deleteConfirm}
							<button
								onclick={() => (deleteConfirm = true)}
								class="w-full py-2 rounded-lg text-sm font-medium transition-colors hover:bg-opacity-10"
								style="color: var(--error); border: 1px solid var(--error);"
							>
								Delete Notebook
							</button>
						{:else}
							<div class="space-y-3">
								<p class="text-sm text-center" style="color: var(--text);">
									Are you sure? This cannot be undone.
								</p>
								<div class="flex gap-2">
									<button
										onclick={() => (deleteConfirm = false)}
										class="flex-1 py-2 rounded-lg text-sm font-medium"
										style="background-color: var(--background); color: var(--text);"
									>
										Cancel
									</button>
									<button
										onclick={handleDelete}
										disabled={loading}
										class="flex-1 py-2 rounded-lg text-sm font-medium text-white"
										style="background-color: var(--error);"
									>
										{loading ? 'Deleting...' : 'Confirm Delete'}
									</button>
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
