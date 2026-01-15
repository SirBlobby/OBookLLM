<script lang="ts">
	import Icon from '@iconify/svelte';
	import { marked } from 'marked';

	let {
		messages,
		loading,
		onSendMessage,
		onShare,
		onSettings,
		selectedSourceCount = 0
	}: {
		messages: {
			role: 'user' | 'assistant';
			content: string;
			citations?: Record<string, { name: string; excerpts: string[] }>;
		}[];
		loading: boolean;
		onSendMessage: (text: string) => void;
		onShare: () => void;
		onSettings: () => void;
		selectedSourceCount?: number;
	} = $props();
	let input = $state('');
	let chatContainer = $state<HTMLElement>();

	function handleSend() {
		if (!input.trim() || loading) return;
		onSendMessage(input);
		input = '';
	}

	$effect(() => {
		// Track length and last message content to trigger scroll on streaming updates
		const _len = messages.length;
		const _lastContent = messages[_len - 1]?.content;

		if (chatContainer) {
			chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
		}
	});

	let activeTooltip = $state<{ id: string; data: any } | null>(null);
	let tooltipPos = $state({ x: 0, y: 0 });

	function toggleTooltip(id: string, citation: any, event: MouseEvent) {
		event.stopPropagation();

		if (activeTooltip?.id === id) {
			activeTooltip = null;
			return;
		}

		const target = (event.target as HTMLElement).closest('button') || (event.target as HTMLElement);
		const rect = target.getBoundingClientRect();

		activeTooltip = { id, data: citation };
		tooltipPos = {
			x: rect.left + rect.width / 2,
			y: rect.top - 8 // 8px gap
		};
	}

	function closeTooltips() {
		activeTooltip = null;
	}

	function renderContent(msg: any) {
		let content = msg.content;
		const citations = msg.citations || {};

		// first render markdown
		try {
			content = marked.parse(content);
		} catch (e) {
			console.error(e);
		}

		// then replace citations [1], [2] with buttons
		return content.replace(/\[(\d+)\]/g, (match: string, id: string) => {
			const citation = citations[id];
			if (!citation) return match;

			const tooltipId = `tooltip-${Math.random().toString(36).substr(2, 9)}`;
			// We can't use Svelte events in HTML strings, so we'll handle clicks globally or via bubbling
			// Using a data attribute to identify the citation
			return `<button class="citation-btn" data-citation-id="${id}" data-citation-text="${encodeURIComponent(citation.excerpts?.[0] || '')}" data-citation-source="${encodeURIComponent(citation.name || '')}">${id}</button>`;
		});
	}
</script>

<div class="flex-1 flex flex-col" style="background-color: var(--background);">
	<!-- Chat Header -->
	<div
		class="h-14 flex items-center px-6 justify-between"
		style="border-bottom: 1px solid var(--border);"
	>
		<h2 class="font-semibold" style="color: var(--text);">Chat</h2>
		<div class="flex items-center gap-3">
			<button
				style="color: var(--text-muted);"
				onclick={onShare}
				class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
			>
				<Icon icon="mdi:share-variant-outline" width="20" />
			</button>
			<button
				style="color: var(--text-muted);"
				onclick={onSettings}
				class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
			>
				<Icon icon="mdi:dots-horizontal" width="20" />
			</button>
		</div>
	</div>

	<!-- Messages -->
	<div
		bind:this={chatContainer}
		class="flex-1 overflow-y-auto p-6 space-y-6"
		style="background-color: var(--background-light);"
	>
		{#each messages as msg}
			<div class="flex gap-4 {msg.role === 'user' ? 'flex-row-reverse' : ''}">
				<!-- Avatar -->
				<div
					class="w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-white"
					style="background-color: {msg.role === 'user' ? 'var(--primary)' : 'var(--success)'};"
				>
					<Icon icon={msg.role === 'user' ? 'mdi:account' : 'mdi:robot'} width="18" />
				</div>

				<!-- Bubble -->
				<div
					class="px-5 py-3 rounded-lg text-sm leading-relaxed shadow-sm {msg.role === 'user'
						? 'rounded-tr-none text-white'
						: 'rounded-tl-none markdown-content'}"
					style="background-color: {msg.role === 'user'
						? 'var(--primary)'
						: 'var(--background)'}; color: {msg.role === 'user'
						? 'white'
						: 'var(--text)'}; {msg.role !== 'user' ? 'border: 1px solid var(--border);' : ''}"
				>
					{#if msg.role === 'user'}
						{msg.content}
					{:else}
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div
							class="message-content"
							onclick={(e) => {
								const target = e.target as HTMLElement;
								if (target.classList.contains('citation-btn')) {
									e.stopPropagation();
									const id = target.dataset.citationId;
									const text = decodeURIComponent(target.dataset.citationText || '');
									const source = decodeURIComponent(target.dataset.citationSource || '');

									// Toggle valid tooltip
									if (activeTooltip?.id === id) {
										activeTooltip = null;
									} else if (id) {
										const citation = msg.citations?.[id];
										if (citation) {
											toggleTooltip(id, citation, e);
										}
									}
								} else {
									// Close tooltip if clicking elsewhere in message
									activeTooltip = null;
								}
							}}
						>
							{@html renderContent(msg)}

							{#if msg.citations && Object.keys(msg.citations).length > 0}
								<div class="mt-4 pt-3 border-t border-black/10 dark:border-white/10">
									<p class="text-xs font-semibold mb-2 opacity-70">Sources used:</p>
									<div class="flex flex-wrap gap-2">
										{#each Object.entries(msg.citations) as [id, citation]}
											<button
												class="text-xs flex items-center gap-1.5 px-2 py-1 rounded bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
												class:ring-1={activeTooltip?.id === id}
												class:ring-primary={activeTooltip?.id === id}
												onclick={(e) => toggleTooltip(id, citation, e)}
											>
												<span
													class="w-4 h-4 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold"
												>
													{id}
												</span>
												<span class="opacity-80 truncate max-w-[150px]">{citation.name}</span>
											</button>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		{/each}

		{#if loading && messages[messages.length - 1].role === 'user'}
			<div class="flex gap-4">
				<div
					class="w-8 h-8 rounded-full flex items-center justify-center text-white"
					style="background-color: var(--success);"
				>
					<Icon icon="mdi:robot" width="18" />
				</div>
				<div
					class="px-5 py-3 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2"
					style="background-color: var(--background); border: 1px solid var(--border);"
				>
					<span
						class="w-2 h-2 rounded-full animate-bounce"
						style="background-color: var(--text-muted);"
					></span>
					<span
						class="w-2 h-2 rounded-full animate-bounce"
						style="background-color: var(--text-muted); animation-delay: 0.1s;"
					></span>
					<span
						class="w-2 h-2 rounded-full animate-bounce"
						style="background-color: var(--text-muted); animation-delay: 0.2s;"
					></span>
				</div>
			</div>
		{/if}
	</div>

	<!-- Input Area -->
	<div
		class="p-4"
		style="border-top: 1px solid var(--border); background-color: var(--background);"
	>
		<div class="relative">
			<input
				type="text"
				bind:value={input}
				disabled={selectedSourceCount === 0}
				onkeydown={(e) => e.key === 'Enter' && handleSend()}
				placeholder={selectedSourceCount === 0
					? 'Select at least one source to chat'
					: 'Type a message...'}
				class="w-full pl-5 pr-24 py-3 rounded focus:outline-none text-sm disabled:opacity-50 disabled:cursor-not-allowed"
				style="background-color: var(--background-light); border: 1px solid var(--border); color: var(--text);"
			/>
			{#if selectedSourceCount > 0}
				<div
					class="absolute right-12 top-0 h-full flex items-center text-xs font-medium mr-2 pointer-events-none"
					style="color: var(--text-muted);"
				>
					{selectedSourceCount} source{selectedSourceCount !== 1 ? 's' : ''}
				</div>
			{/if}
			<button
				onclick={handleSend}
				class="absolute right-2 top-1.5 p-1.5 rounded-full text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				style="background-color: var(--primary);"
				disabled={!input.trim() || loading || selectedSourceCount === 0}
			>
				<Icon icon="mdi:arrow-up" width="20" />
			</button>
		</div>
		<div class="text-center mt-2 text-xs" style="color: var(--text-muted);">
			AI can make mistakes. Check important info.
		</div>
	</div>
</div>

<!-- Global Tooltip -->
{#if activeTooltip}
	<div
		class="fixed z-50 animate-in fade-in zoom-in-95 duration-200"
		style="left: {tooltipPos.x}px; top: {tooltipPos.y}px; transform: translate(-50%, -100%);"
	>
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="citation-card" onclick={(e) => e.stopPropagation()}>
			<div class="citation-header">
				<Icon icon="mdi:file-document-outline" width="16" />
				<span class="truncate">{activeTooltip.data.name}</span>
				<button
					class="ml-auto hover:bg-white/10 p-1 rounded"
					onclick={() => (activeTooltip = null)}
				>
					<Icon icon="mdi:close" width="14" />
				</button>
			</div>
			<div class="citation-body custom-scrollbar">
				"{activeTooltip.data.excerpts?.[0]}"
			</div>
			<!-- Arrow -->
			<div
				class="absolute bottom-[-6px] left-1/2 -translate-x-1/2 w-3 h-3 rotate-45 border-b border-r border-[#333] dark:border-gray-600 bg-[#1e1e1e] dark:bg-gray-800"
			></div>
		</div>
	</div>
{/if}

<style>
	/* Markdown Content Styling */
	:global(.markdown-content p) {
		margin-bottom: 0.75em;
	}
	:global(.markdown-content p:last-child) {
		margin-bottom: 0;
	}
	:global(.markdown-content strong) {
		font-weight: 600;
		color: var(--text);
	}
	:global(.markdown-content em) {
		font-style: italic;
	}
	:global(.markdown-content ul) {
		list-style-type: disc;
		padding-left: 1.5em;
		margin-bottom: 0.75em;
	}
	:global(.markdown-content ol) {
		list-style-type: decimal;
		padding-left: 1.5em;
		margin-bottom: 0.75em;
	}
	:global(.markdown-content li) {
		margin-bottom: 0.25em;
	}
	:global(.markdown-content code) {
		background-color: rgba(0, 0, 0, 0.2);
		padding: 0.2em 0.4em;
		border-radius: 4px;
		font-family: monospace;
		font-size: 0.9em;
	}
	:global(.markdown-content pre) {
		background-color: rgba(0, 0, 0, 0.3);
		padding: 1em;
		border-radius: 8px;
		overflow-x: auto;
		margin-bottom: 1em;
	}
	:global(.markdown-content pre code) {
		background-color: transparent;
		padding: 0;
		color: inherit;
	}
	:global(.markdown-content h1, .markdown-content h2, .markdown-content h3) {
		font-weight: 600;
		margin-top: 1em;
		margin-bottom: 0.5em;
		color: var(--text);
	}
	:global(.markdown-content h1) {
		font-size: 1.5em;
	}
	:global(.markdown-content h2) {
		font-size: 1.25em;
	}
	:global(.markdown-content h3) {
		font-size: 1.1em;
	}
	:global(.markdown-content a) {
		color: var(--primary);
		text-decoration: underline;
	}
	:global(.markdown-content blockquote) {
		border-left: 3px solid var(--border);
		padding-left: 1em;
		color: var(--text-muted);
		margin-bottom: 1em;
	}

	/* Citation Styles */
	:global(.citation-btn) {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 1.4em;
		padding: 0 0.2em; /* Chip padding */
		height: 1.4em;
		border-radius: 4px; /* Square/Chip shape */
		background-color: rgba(139, 92, 246, 0.15);
		color: var(--primary);
		font-size: 0.75em;
		font-weight: 600;
		vertical-align: 0.1em; /* Slight lift, not full super */
		margin: 0 2px;
		cursor: pointer;
		border: 1px solid rgba(139, 92, 246, 0.3);
		transition: all 0.2s;
	}
	:global(.citation-btn:hover) {
		background-color: var(--primary);
		color: white;
		transform: scale(1.1);
	}

	.message-content {
		position: relative;
	}

	.citation-card {
		/* Removed absolute positioning */
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 12px;
		/* margin-bottom removed */
		box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.4);
		/* z-index removed */
		width: 320px; /* Fixed width for better look */
		max-width: 90vw;
		background-color: #1e1e1e; /* Dark theme default for tooltip look */
		color: #e5e5e5;
	}

	@keyframes slideUp {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.citation-header {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 0.85em;
		font-weight: 600;
		color: var(--text);
		margin-bottom: 8px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}

	.citation-body {
		font-size: 0.85em;
		line-height: 1.5;
		color: var(--text-muted);
		max-height: 150px;
		overflow-y: auto;
		font-style: italic;
	}
</style>
