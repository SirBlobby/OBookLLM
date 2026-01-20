<script lang="ts">
	import Icon from '@iconify/svelte';
	import AddSourceModal from './AddSourceModal.svelte';

	interface Source {
		name: string;
		type: string; // pdf, audio, text, docx, json, csv, excel, yaml, html, code, image
		status: 'ready' | 'processing';
		content?: string;
	}

	interface Props {
		sources: Source[];
		onUpload: (e: Event) => void;
		onUploadFile?: (file: File, type: string) => void;
		onAddText?: (text: string) => void;
		onAddUrl?: (url: string) => void;
		onDelete?: (sourceName: string) => void;
		onView?: (source: Source) => void;
	}

	let {
		sources,
		onUpload,
		onUploadFile,
		onAddText,
		onAddUrl,
		onDelete,
		onView,
		selectedSources = $bindable([])
	}: Props & { selectedSources?: string[] } = $props();

	let showModal = $state(false);

	// Derived state for "Select All" checkbox
	let allSelected = $derived(sources.length > 0 && selectedSources.length === sources.length);

	// Map file types to icons
	function getTypeIcon(type: string): string {
		const iconMap: Record<string, string> = {
			pdf: 'mdi:file-pdf-box',
			audio: 'mdi:microphone',
			text: 'mdi:text-box',
			docx: 'mdi:file-word',
			json: 'mdi:code-json',
			csv: 'mdi:file-delimited',
			excel: 'mdi:file-excel',
			yaml: 'mdi:file-code',
			xml: 'mdi:xml',
			html: 'mdi:language-html5',
			code: 'mdi:code-braces',
			image: 'mdi:image',
			markdown: 'mdi:language-markdown',
			web: 'mdi:web'
		};
		return iconMap[type] || 'mdi:file-document';
	}

	// Map file types to colors
	function getTypeColor(type: string): string {
		const colorMap: Record<string, string> = {
			pdf: '#ef4444',
			audio: '#8b5cf6',
			text: '#22c55e',
			docx: '#3b82f6',
			json: '#f59e0b',
			csv: '#10b981',
			excel: '#22c55e',
			yaml: '#06b6d4',
			xml: '#ea580c',
			html: '#f97316',
			code: '#6366f1',
			image: '#ec4899',
			markdown: '#64748b',
			web: '#6366f1'
		};
		return colorMap[type] || '#6b7280';
	}

	function toggleAll() {
		if (allSelected) {
			selectedSources = [];
		} else {
			selectedSources = sources.map((s) => s.name);
		}
	}

	function toggleSource(name: string) {
		if (selectedSources.includes(name)) {
			selectedSources = selectedSources.filter((s) => s !== name);
		} else {
			selectedSources = [...selectedSources, name];
		}
	}

	function handleUploadFile(file: File, type: string) {
		if (onUploadFile) {
			onUploadFile(file, type);
		} else {
			const dataTransfer = new DataTransfer();
			dataTransfer.items.add(file);
			const event = new Event('change', { bubbles: true });
			const input = document.createElement('input');
			input.type = 'file';
			input.files = dataTransfer.files;
			Object.defineProperty(event, 'target', { value: input, writable: false });
			onUpload(event);
		}
	}

	function handleAddText(text: string) {
		if (onAddText) {
			onAddText(text);
		}
	}

	function handleAddUrl(url: string) {
		if (onAddUrl) {
			onAddUrl(url);
		}
	}
</script>

<div
	class="w-72 flex flex-col transition-colors h-full"
	style="background-color: var(--background-light); border-right: 1px solid var(--border);"
>
	<div
		class="p-5 flex justify-between items-center shrink-0 h-20"
		style="border-bottom: 1px solid var(--border);"
	>
		<h2 class="font-bold text-lg tracking-tight" style="color: var(--text);">Sources</h2>
		<button
			style="background-color: var(--primary); color: white;"
			onclick={() => (showModal = true)}
			class="p-1.5 rounded transition-transform active:scale-95 shadow-sm shadow-primary/20 hover:opacity-90"
			title="Add source"
		>
			<Icon icon="mdi:plus" width="20" />
		</button>
	</div>

	<!-- Select All Header -->
	{#if sources.length > 0}
		<div class="px-5 py-3 flex items-center gap-3 border-b border-dashed border-border/50">
			<button
				onclick={toggleAll}
				class="text-gray-400 hover:text-primary transition-colors active:scale-95"
				style="color: {allSelected ? 'var(--primary)' : 'var(--text-muted)'}"
			>
				<Icon
					icon={allSelected ? 'mdi:checkbox-marked' : 'mdi:checkbox-blank-outline'}
					width="22"
				/>
			</button>
			<span
				class="text-xs font-semibold uppercase tracking-wider opacity-70"
				style="color: var(--text-muted);">Select all</span
			>
		</div>
	{/if}

	<div class="flex-1 overflow-y-auto p-3 space-y-2">
		{#if sources.length === 0}
			<div class="text-center p-8 text-sm" style="color: var(--text-muted);">
				<div
					class="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
					style="background-color: var(--background);"
				>
					<Icon icon="mdi:file-document-plus-outline" width="32" style="color: var(--border);" />
				</div>
				<p class="font-medium mb-1">No sources yet</p>
				<p class="text-xs">Add documents, data files, code, or media</p>
			</div>
		{/if}

		{#each sources as source}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<div
				class="group p-3 rounded flex items-center gap-3 transition-all duration-200 relative cursor-pointer border hover:shadow-sm"
				style="background-color: var(--background); border-color: {selectedSources.includes(
					source.name
				)
					? 'var(--primary)'
					: 'transparent'};"
				class:border-transparent={!selectedSources.includes(source.name)}
				onclick={() => onView?.(source)}
				role="button"
				tabindex="0"
			>
				<!-- Checkbox -->
				<button
					onclick={(e) => {
						e.stopPropagation();
						toggleSource(source.name);
					}}
					class="shrink-0 transition-transform active:scale-95 p-1 -ml-1"
					style="color: {selectedSources.includes(source.name)
						? 'var(--primary)'
						: 'var(--text-muted)'}"
				>
					<Icon
						icon={selectedSources.includes(source.name)
							? 'mdi:checkbox-marked'
							: 'mdi:checkbox-blank-outline'}
						width="22"
					/>
				</button>

				<div class="shrink-0">
					<div
						class="w-8 h-8 rounded flex items-center justify-center shadow-sm"
						style="background-color: {getTypeColor(source.type)}15;"
					>
						<Icon
							icon={getTypeIcon(source.type)}
							width="20"
							style="color: {getTypeColor(source.type)};"
						/>
					</div>
				</div>
				<div class="flex-1 min-w-0">
					<div
						class="text-sm font-medium truncate leading-tight mb-0.5"
						style="color: var(--text);"
					>
						{source.name}
					</div>
					<div
						class="text-[11px] font-medium flex items-center gap-1.5"
						style="color: var(--text-muted);"
					>
						{#if source.status === 'processing'}
							<span class="flex items-center gap-1 text-yellow-500">
								<Icon icon="mdi:loading" class="animate-spin" width="12" />
								<span>Processing...</span>
							</span>
						{:else}
							<span class="flex items-center gap-1 text-green-500">
								<Icon icon="mdi:check-circle" width="12" />
								<span>Ready</span>
							</span>
						{/if}
					</div>
				</div>

				{#if onDelete}
					<button
						onclick={(e) => {
							e.stopPropagation();
							onDelete(source.name);
						}}
						class="w-8 h-8 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-red-500 transition-all absolute right-2 top-1/2 -translate-y-1/2 bg-background md:bg-transparent shadow-sm md:shadow-none"
						title="Remove"
						aria-label="Remove source"
					>
						<Icon icon="mdi:trash-can-outline" width="18" />
					</button>
				{/if}
			</div>
		{/each}
	</div>
</div>

<AddSourceModal
	isOpen={showModal}
	onClose={() => (showModal = false)}
	onUploadFile={handleUploadFile}
	onAddText={handleAddText}
	onAddUrl={handleAddUrl}
/>
