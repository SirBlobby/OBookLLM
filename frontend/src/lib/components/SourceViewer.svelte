<script lang="ts">
	import Icon from '@iconify/svelte';
	import { onMount } from 'svelte';
	import PDFViewer from './PDFViewer.svelte';
	import AudioPlayer from './AudioPlayer.svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	interface Props {
		source: {
			name: string;
			content: string;
			type: string;
		};
		rawUrl?: string;
		currentTime?: number;
		onTimeUpdate?: (time: number) => void;
	}

	let { source, rawUrl, currentTime = 0, onTimeUpdate }: Props = $props();

	let ext = $derived(source.name.toLowerCase().split('.').pop() || '');

	const typeConfig: Record<string, { icon: string; color: string; title: string }> = {
		pdf: { icon: 'mdi:file-pdf-box', color: '#ef4444', title: 'PDF Document' },
		audio: { icon: 'mdi:microphone', color: '#8b5cf6', title: 'Audio' },
		text: { icon: 'mdi:text-box', color: '#22c55e', title: 'Text' },
		markdown: { icon: 'mdi:language-markdown', color: '#64748b', title: 'Markdown' },
		docx: { icon: 'mdi:file-word', color: '#3b82f6', title: 'Word Document' },
		json: { icon: 'mdi:code-json', color: '#f59e0b', title: 'JSON Data' },
		csv: { icon: 'mdi:file-delimited', color: '#10b981', title: 'CSV Data' },
		excel: { icon: 'mdi:file-excel', color: '#22c55e', title: 'Excel Spreadsheet' },
		yaml: { icon: 'mdi:file-code', color: '#06b6d4', title: 'YAML Data' },
		xml: { icon: 'mdi:xml', color: '#ea580c', title: 'XML Data' },
		html: { icon: 'mdi:language-html5', color: '#f97316', title: 'HTML' },
		code: { icon: 'mdi:code-braces', color: '#6366f1', title: 'Source Code' },
		image: { icon: 'mdi:image', color: '#ec4899', title: 'Image' },
		web: { icon: 'mdi:web', color: '#6366f1', title: 'Website' }
	};

	let config = $derived(typeConfig[source.type] || typeConfig.text);

	let isMarkdownData = $derived(['csv', 'excel', 'markdown'].includes(source.type));
	let isCodeData = $derived(['json', 'yaml', 'xml', 'code', 'html'].includes(source.type));

	let renderedContent = $state('');

	$effect(() => {
		if (isMarkdownData) {
			try {
				const html = marked.parse(source.content);
				renderedContent = DOMPurify.sanitize(html as string);
			} catch (e) {
				renderedContent = `<pre>${source.content}</pre>`;
			}
		}
	});

	function hasCodeBlocks(content: string): boolean {
		return /```[\s\S]*?```/.test(content);
	}

	function parseTimestamp(ts: string): number {
		const parts = ts.split(':').map(Number);
		if (parts.length === 2) return parts[0] * 60 + parts[1];
		if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
		return 0;
	}

	function formatTranscriptWithHighlight(content: string, time: number) {
		if (!content) return '';

		const lines = content.split('\n');
		return lines
			.map((line) => {
				const match = line.match(/\[(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\]/);
				let isActive = false;

				if (match) {
					const startTime = parseTimestamp(match[1]);
					const endTime = parseTimestamp(match[2]);
					isActive = time >= startTime && time < endTime;
				}

				// Sanitize
				let safeLine = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

				// Style the timestamp
				safeLine = safeLine.replace(
					/\[(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})\]/g,
					'<span style="background-color: rgba(139, 92, 246, 0.15); color: #8b5cf6; font-family: monospace; font-size: 0.85em; font-weight: 600; padding: 2px 6px; border-radius: 4px; margin-right: 8px; user-select: none;">$1</span>'
				);

				if (isActive) {
					return `<div class="transcript-line active" style="background-color: rgba(139, 92, 246, 0.1); padding: 4px 8px; margin: 2px -8px; border-radius: 4px; border-left: 3px solid #8b5cf6;">${safeLine}</div>`;
				}
				return `<div class="transcript-line" style="padding: 4px 8px; margin: 2px -8px;">${safeLine}</div>`;
			})
			.join('');
	}

	let formattedTranscript = $derived(
		source.type === 'audio'
			? formatTranscriptWithHighlight(source.content, currentTime)
			: source.content
	);
</script>

<div class="source-viewer">
	{#if source.type === 'pdf' && rawUrl}
		<div class="h-full w-full min-h-[60vh]">
			<PDFViewer url={rawUrl} />
		</div>
	{:else if source.type === 'audio' && rawUrl}
		<div class="flex flex-col gap-4">
			<AudioPlayer url={rawUrl} title={source.name} onTimeUpdate={(time) => onTimeUpdate?.(time)} />
			{#if source.content}
				<div class="border-t pt-3" style="border-color: var(--border);">
					<h4
						class="text-xs font-semibold mb-2 uppercase tracking-wide"
						style="color: var(--text-muted);"
					>
						Transcript
					</h4>
					<div class="text-sm whitespace-pre-wrap" style="color: var(--text-muted);">
						{@html formattedTranscript}
					</div>
				</div>
			{/if}
		</div>
	{:else if source.type === 'image' && rawUrl}
		<div class="flex flex-col gap-4">
			<div class="rounded-lg overflow-hidden border" style="border-color: var(--border);">
				<img src={rawUrl} alt={source.name} class="max-w-full h-auto" />
			</div>
			{#if source.content}
				<div class="border-t pt-3" style="border-color: var(--border);">
					<h4
						class="text-xs font-semibold mb-2 uppercase tracking-wide"
						style="color: var(--text-muted);"
					>
						<Icon icon="mdi:text-recognition" width="14" class="inline mr-1" />
						Extracted Text (OCR)
					</h4>
					<div
						class="text-sm whitespace-pre-wrap rounded-lg p-3"
						style="color: var(--text); background-color: var(--background);"
					>
						{source.content}
					</div>
				</div>
			{/if}
		</div>
	{:else if isCodeData}
		<div class="rounded-lg overflow-hidden border" style="border-color: var(--border);">
			<div
				class="flex items-center justify-between px-3 py-2"
				style="background-color: var(--background); border-bottom: 1px solid var(--border);"
			>
				<div class="flex items-center gap-2">
					<Icon icon={config.icon} width="16" style="color: {config.color};" />
					<span class="text-xs font-medium" style="color: var(--text-muted);">
						{config.title}
					</span>
				</div>
				<span
					class="text-xs px-2 py-0.5 rounded"
					style="background-color: {config.color}20; color: {config.color};"
				>
					.{ext}
				</span>
			</div>
			<pre
				class="p-4 overflow-x-auto text-sm"
				style="background-color: var(--background-light); color: var(--text); margin: 0;"><code
					>{source.content}</code
				></pre>
		</div>
	{:else if isMarkdownData}
		<div
			class="markdown-preview prose prose-sm max-w-none dark:prose-invert"
			style="color: var(--text);"
		>
			{@html renderedContent}
		</div>
	{:else}
		<div class="whitespace-pre-wrap text-sm" style="color: var(--text);">
			{source.content}
		</div>
	{/if}
</div>

<style>
	.source-viewer :global(.markdown-preview) {
		line-height: 1.6;
	}

	.source-viewer :global(.markdown-preview table) {
		width: 100%;
		border-collapse: collapse;
		margin: 1em 0;
		font-size: 0.85em;
	}

	.source-viewer :global(.markdown-preview th),
	.source-viewer :global(.markdown-preview td) {
		padding: 8px 12px;
		border: 1px solid var(--border);
		text-align: left;
	}

	.source-viewer :global(.markdown-preview th) {
		background-color: var(--background);
		font-weight: 600;
	}

	.source-viewer :global(.markdown-preview tr:nth-child(even)) {
		background-color: rgba(0, 0, 0, 0.02);
	}

	@media (prefers-color-scheme: dark) {
		.source-viewer :global(.markdown-preview tr:nth-child(even)) {
			background-color: rgba(255, 255, 255, 0.02);
		}
	}

	.source-viewer :global(.markdown-preview h1),
	.source-viewer :global(.markdown-preview h2),
	.source-viewer :global(.markdown-preview h3) {
		margin-top: 1.5em;
		margin-bottom: 0.5em;
		font-weight: 600;
		line-height: 1.25;
	}

	.source-viewer :global(.markdown-preview h1) {
		font-size: 1.5em;
		border-bottom: 1px solid var(--border);
		padding-bottom: 0.3em;
	}
	.source-viewer :global(.markdown-preview h2) {
		font-size: 1.25em;
		border-bottom: 1px solid var(--border);
		padding-bottom: 0.3em;
	}
	.source-viewer :global(.markdown-preview h3) {
		font-size: 1.1em;
	}

	.source-viewer pre {
		font-family:
			ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
	}
</style>
