<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import SourcePanel from '$lib/components/SourcePanel.svelte';
	import ChatArea from '$lib/components/ChatArea.svelte';
	import NotebookSettingsModal from '$lib/components/NotebookSettingsModal.svelte';
	import SourceViewer from '$lib/components/SourceViewer.svelte';
	import PDFViewer from '$lib/components/PDFViewer.svelte';
	import AudioPlayer from '$lib/components/AudioPlayer.svelte';
	import { PUBLIC_BACKEND_URL } from '$env/static/public';
	import Icon from '@iconify/svelte';

	let notebookId = $derived($page.params.id ?? '');
	let messages = $state<
		{
			role: 'user' | 'assistant';
			content: string;
			citations?: Record<string, { name: string; excerpts: string[] }>;
		}[]
	>([
		{
			role: 'assistant',
			content:
				'Hello! Upload a document to get started or ask me anything about your existing sources.'
		}
	]);
	let loading = $state(false);
	let sources = $state<
		{
			name: string;
			type: string; // pdf, audio, text, docx, json, csv, excel, yaml, xml, html, code, image, markdown
			status: 'ready' | 'processing';
			content?: string;
		}[]
	>([]);
	let selectedSources = $state<string[]>([]);
	let notebookTitle = $state('Notebook');
	let showSettingsModal = $state(false);
	let settingsInitialTab = $state<'settings' | 'share'>('settings');

	async function sendMessage(text: string) {
		if (!text.trim()) return;

		messages = [...messages, { role: 'user', content: text }];
		loading = true;

		try {
			const response = await fetch(`${PUBLIC_BACKEND_URL}/chat`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					notebook_id: notebookId,
					messages: messages,
					selected_sources: selectedSources
				})
			});

			if (!response.body) throw new Error('No response body');

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let assistantMsg = '';
			let msgIndex = -1;

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const chunk = decoder.decode(value);
				assistantMsg += chunk;

				// Initialize message on first chunk
				if (msgIndex === -1) {
					messages = [...messages, { role: 'assistant', content: '', citations: {} }];
					msgIndex = messages.length - 1;
				}

				// Strip citation data while streaming
				const delim = '\n\n---CITATIONS---\n';
				if (assistantMsg.includes(delim)) {
					messages[msgIndex].content = assistantMsg.split(delim)[0];
				} else {
					messages[msgIndex].content = assistantMsg;
				}
			}

			// Parse citations after stream ends
			const delim = '\n\n---CITATIONS---\n';
			if (assistantMsg.includes(delim)) {
				const [content, citationJson] = assistantMsg.split(delim);
				messages[msgIndex].content = content;
				try {
					messages[msgIndex].citations = JSON.parse(citationJson);
				} catch (e) {
					console.error('Failed to parse citations:', e);
				}
			}
		} catch (e) {
			console.error(e);
			messages = [...messages, { role: 'assistant', content: 'Sorry, I encountered an error.' }];
		} finally {
			loading = false;
		}
	}

	function getFileType(filename: string): 'pdf' | 'audio' | 'text' {
		const lower = filename.toLowerCase();
		if (lower.endsWith('.pdf')) return 'pdf';
		if (lower.match(/\.(mp3|wav|m4a|ogg|flac)$/)) return 'audio';
		return 'text';
	}

	async function pollForCompletion(filename: string) {
		const maxAttempts = 60; // 2 minutes (2s * 60)
		for (let i = 0; i < maxAttempts; i++) {
			await new Promise((r) => setTimeout(r, 2000));
			try {
				const res = await fetch(`${PUBLIC_BACKEND_URL}/notebooks/${notebookId}`);
				if (res.ok) {
					const data = await res.json();
					const source = data.sources?.find((s: any) => s.name === filename);

					if (source) {
						const idx = sources.findIndex((s) => s.name === filename);
						if (idx !== -1) {
							// If status changed to ready or error, update and stop polling
							if (source.status === 'ready' || source.status === 'error') {
								sources[idx] = source;
								sources = [...sources]; // Trigger reactivity

								// Auto-select ready sources
								if (source.status === 'ready' && !selectedSources.includes(source.name)) {
									selectedSources = [...selectedSources, source.name];
								}
								return;
							}
						}
					}
				}
			} catch (e) {
				console.error('Polling error', e);
			}
		}
	}

	async function handleFileUpload(file: File, type: string) {
		const formData = new FormData();
		formData.append('file', file);
		formData.append('notebook_id', notebookId ?? '');

		// Add to sources list with processing status
		sources = [...sources, { name: file.name, type, status: 'processing' }];

		try {
			const response = await fetch(`${PUBLIC_BACKEND_URL}/upload`, {
				method: 'POST',
				body: formData
			});

			if (response.ok) {
				// Start polling for completion (status: 'ready' and content)
				pollForCompletion(file.name);
			} else {
				// Remove failed source
				sources = sources.filter((s) => !(s.name === file.name && s.status === 'processing'));
			}
		} catch (e) {
			console.error('Upload failed', e);
			// Remove failed source
			sources = sources.filter((s) => !(s.name === file.name && s.status === 'processing'));
		}
	}

	async function handleAddText(text: string) {
		// Create a text source with a timestamp name
		const timestamp = new Date().toLocaleTimeString();
		const sourceName = `Text Note (${timestamp}).txt`;

		// Add to sources list
		sources = [...sources, { name: sourceName, type: 'text', status: 'processing' }];

		try {
			// Create a blob from the text and upload it
			const blob = new Blob([text], { type: 'text/plain' });
			const file = new File([blob], sourceName, { type: 'text/plain' });

			const formData = new FormData();
			formData.append('file', file);
			formData.append('notebook_id', notebookId ?? '');

			const response = await fetch(`${PUBLIC_BACKEND_URL}/upload`, {
				method: 'POST',
				body: formData
			});

			if (response.ok) {
				pollForCompletion(sourceName);
			} else {
				sources = sources.filter((s) => !(s.name === sourceName && s.status === 'processing'));
			}
		} catch (e) {
			console.error('Failed to add text', e);
			sources = sources.filter((s) => !(s.name === sourceName && s.status === 'processing'));
		}
	}

	async function handleAddUrl(url: string) {
		if (!url.trim()) return;

		// Add optimistic source
		const sourceName = url; // Use URL as name for now

		sources = [
			...sources,
			{
				name: sourceName,
				type: 'web',
				status: 'processing'
			}
		];

		try {
			const response = await fetch(`${PUBLIC_BACKEND_URL}/upload/url`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					notebook_id: notebookId,
					url: url
				})
			});

			if (response.ok) {
				pollForCompletion(sourceName);
			} else {
				sources = sources.filter((s) => !(s.name === sourceName && s.status === 'processing'));
			}
		} catch (e) {
			console.error('Failed to add URL', e);
			sources = sources.filter((s) => !(s.name === sourceName && s.status === 'processing'));
		}
	}

	// Legacy handler for backward compatibility
	function handleLegacyUpload(e: Event) {
		const target = e.target as HTMLInputElement;
		if (!target.files?.length) return;

		const file = target.files[0];
		handleFileUpload(file, getFileType(file.name));
	}

	$effect(() => {
		// Reset and load when notebookId changes
		if (!notebookId) return;

		messages = [
			{
				role: 'assistant',
				content:
					'Hello! Upload a document to get started or ask me anything about your existing sources.'
			}
		];
		sources = [];
		selectedSources = [];
		notebookTitle = 'Notebook';

		async function loadNotebook() {
			try {
				const res = await fetch(`${PUBLIC_BACKEND_URL}/notebooks/${notebookId}`);
				if (res.ok) {
					const data = await res.json();
					if (data.title) notebookTitle = data.title;
					if (data.sources) {
						sources = data.sources;
						// Default to all selected on initial load if empty
						if (selectedSources.length === 0 && sources.length > 0) {
							selectedSources = sources.map((s: any) => s.name);
						}
					}
					if (data.messages && data.messages.length > 0) {
						messages = data.messages.map((msg: any) => {
							if (
								msg.role === 'assistant' &&
								typeof msg.content === 'string' &&
								msg.content.includes('---CITATIONS---')
							) {
								const parts = msg.content.split('---CITATIONS---');
								if (parts.length > 1) {
									try {
										// The delimiter might have surrounding newlines, so we clean up the content part
										const content = parts[0].trim();
										const jsonStr = parts[1].trim();
										const citations = JSON.parse(jsonStr);
										return {
											...msg,
											content,
											citations
										};
									} catch (e) {
										console.error('Failed to parse citations for message', e);
										return msg;
									}
								}
							}
							return msg;
						});
					}
				}
			} catch (e) {
				console.error('Failed to load notebook data', e);
			}
		}

		loadNotebook();
	});

	function handleShare() {
		settingsInitialTab = 'share';
		showSettingsModal = true;
	}

	function handleSettings() {
		settingsInitialTab = 'settings';
		showSettingsModal = true;
	}

	function handleRename(newTitle: string) {
		notebookTitle = newTitle;
	}

	async function handleClearHistory() {
		const initialMessage = {
			role: 'assistant' as const,
			content:
				'Hello! Upload a document to get started or ask me anything about your existing sources.'
		};

		// Update local state
		messages = [initialMessage];

		// Update backend
		const res = await fetch(`${PUBLIC_BACKEND_URL}/notebooks/${notebookId}/messages`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify([initialMessage])
		});

		if (!res.ok) {
			throw new Error('Failed to clear history');
		}
	}

	async function handleRemoveSource(sourceName: string) {
		if (!confirm(`Are you sure you want to remove "${sourceName}"?`)) return;

		const originalSources = sources;
		sources = sources.filter((s) => s.name !== sourceName);

		try {
			const res = await fetch(
				`${PUBLIC_BACKEND_URL}/notebooks/${notebookId}/sources/${encodeURIComponent(sourceName)}`,
				{
					method: 'DELETE'
				}
			);
			if (!res.ok) {
				sources = originalSources;
				console.error('Failed to delete source');
			}
		} catch (e) {
			sources = originalSources;
			console.error(e);
		}
	}

	let viewingSource = $state<{
		name: string;
		content: string;
		type: string;
	} | null>(null);
	let audioCurrentTime = $state(0);

	function handleViewSource(source: any) {
		const type = source.type || 'text';
		if (typeof source.content === 'string' || type === 'pdf') {
			viewingSource = {
				name: source.name,
				content: source.content?.trim() === '' ? ' Transcript is empty.' : source.content || '',
				type: type
			};
		} else {
			// If content is missing (undefined), it's a legacy source or didn't update yet
			viewingSource = {
				name: source.name,
				content:
					'No transcript/content available for this source (it may have been uploaded before this feature was added).\n\nPlease delete and re-upload the file to see the content.',
				type: type
			};
		}
	}
</script>

<div class="flex h-full transition-colors" style="background-color: var(--background);">
	<SourcePanel
		{sources}
		bind:selectedSources
		onUpload={handleLegacyUpload}
		onUploadFile={handleFileUpload}
		onAddText={handleAddText}
		onAddUrl={handleAddUrl}
		onDelete={handleRemoveSource}
		onView={handleViewSource}
	/>
	<ChatArea
		{messages}
		{loading}
		selectedSourceCount={selectedSources.length}
		onSendMessage={sendMessage}
		onShare={handleShare}
		onSettings={handleSettings}
	/>

	<NotebookSettingsModal
		isOpen={showSettingsModal}
		{notebookId}
		currentTitle={notebookTitle}
		initialTab={settingsInitialTab}
		onClose={() => (showSettingsModal = false)}
		onRename={handleRename}
		onClearHistory={handleClearHistory}
	/>

	{#if viewingSource}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div
			class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
			onclick={() => (viewingSource = null)}
			role="button"
			tabindex="0"
		>
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<div
				class="bg-background border border-border rounded-xl shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col"
				onclick={(e) => e.stopPropagation()}
				role="document"
				tabindex="0"
				style="background-color: var(--background-light); border: 1px solid var(--border);"
			>
				<div
					class="p-4 border-b border-border flex justify-between items-center shrink-0"
					style="border-bottom: 1px solid var(--border);"
				>
					<h3 class="font-semibold text-lg" style="color: var(--text);">{viewingSource.name}</h3>
					<button
						onclick={() => (viewingSource = null)}
						class="p-1 hover:bg-white/10 rounded transition-colors"
						style="color: var(--text-muted);"
					>
						<Icon icon="mdi:close" width="24" />
					</button>
				</div>
				<div
					class="p-6 overflow-y-auto text-sm whitespace-pre-wrap leading-relaxed font-sans flex-1"
					style="color: var(--text-muted);"
				>
					<SourceViewer
						source={viewingSource}
						rawUrl={`${PUBLIC_BACKEND_URL}/notebooks/${notebookId}/sources/${encodeURIComponent(viewingSource.name)}/raw`}
						currentTime={audioCurrentTime}
						onTimeUpdate={(time) => (audioCurrentTime = time)}
					/>
				</div>
			</div>
		</div>
	{/if}
</div>
