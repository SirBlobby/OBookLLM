<script lang="ts">
	import Icon from '@iconify/svelte';

	interface Props {
		isOpen: boolean;
		onClose: () => void;
		onUploadFile: (file: File, type: string) => void;
		onAddText: (text: string) => void;
		onAddUrl?: (url: string) => void;
	}

	let { isOpen, onClose, onUploadFile, onAddText, onAddUrl }: Props = $props();

	type TabId = 'documents' | 'data' | 'code' | 'media' | 'web' | 'text';

	let activeTab = $state<TabId>('documents');
	let textContent = $state('');
	let urlInput = $state('');
	let dragOver = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);

	const tabs: { id: TabId; label: string; icon: string; color: string }[] = [
		{ id: 'documents', label: 'Documents', icon: 'mdi:file-document', color: '#ef4444' },
		{ id: 'data', label: 'Data', icon: 'mdi:database', color: '#f59e0b' },
		{ id: 'code', label: 'Code', icon: 'mdi:code-braces', color: '#22c55e' },
		{ id: 'media', label: 'Media', icon: 'mdi:image-multiple', color: '#8b5cf6' },
		{ id: 'web', label: 'Web', icon: 'mdi:web', color: '#6366f1' },
		{ id: 'text', label: 'Text', icon: 'mdi:text-box', color: '#3b82f6' }
	];

	const fileTypeGroups: Record<TabId, { extensions: string[]; label: string; icon: string }> = {
		documents: {
			extensions: ['.pdf', '.docx', '.doc', '.txt', '.md', '.html', '.htm'],
			label: 'PDF, Word, Text, Markdown, HTML',
			icon: 'mdi:file-document-multiple'
		},
		data: {
			extensions: ['.json', '.csv', '.xlsx', '.xls', '.yaml', '.yml', '.xml'],
			label: 'JSON, CSV, Excel, YAML, XML',
			icon: 'mdi:table'
		},
		code: {
			extensions: [
				'.py',
				'.js',
				'.ts',
				'.jsx',
				'.tsx',
				'.java',
				'.cpp',
				'.c',
				'.h',
				'.rs',
				'.go',
				'.rb',
				'.php',
				'.swift',
				'.kt',
				'.sql',
				'.sh',
				'.bash'
			],
			label: 'Python, JavaScript, TypeScript, Java, etc.',
			icon: 'mdi:file-code'
		},
		media: {
			extensions: [
				'.mp3',
				'.wav',
				'.m4a',
				'.ogg',
				'.flac',
				'.png',
				'.jpg',
				'.jpeg',
				'.gif',
				'.bmp',
				'.tiff'
			],
			label: 'Audio (MP3, WAV) & Images (PNG, JPG)',
			icon: 'mdi:multimedia'
		},
		web: {
			extensions: [],
			label: 'Website URLs',
			icon: 'mdi:web'
		},
		text: {
			extensions: ['.txt', '.md'],
			label: 'Plain text or Markdown',
			icon: 'mdi:text'
		}
	};

	// Derived value for current tab
	let currentTab = $derived(tabs.find((t) => t.id === activeTab));
	let currentFileGroup = $derived(fileTypeGroups[activeTab]);

	function getAcceptTypes(): string {
		return currentFileGroup?.extensions.join(',') || '*';
	}

	function getFileType(filename: string): string {
		const ext = filename.toLowerCase().split('.').pop() || '';

		// Map extensions to types
		if (['.pdf'].some((e) => filename.endsWith(e))) return 'pdf';
		if (['.docx', '.doc'].some((e) => filename.endsWith(e))) return 'docx';
		if (['.mp3', '.wav', '.m4a', '.ogg', '.flac'].some((e) => filename.endsWith(e))) return 'audio';
		if (['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'].some((e) => filename.endsWith(e)))
			return 'image';
		if (['.json'].some((e) => filename.endsWith(e))) return 'json';
		if (['.csv'].some((e) => filename.endsWith(e))) return 'csv';
		if (['.xlsx', '.xls'].some((e) => filename.endsWith(e))) return 'excel';
		if (['.yaml', '.yml'].some((e) => filename.endsWith(e))) return 'yaml';
		if (['.xml'].some((e) => filename.endsWith(e))) return 'xml';
		if (['.html', '.htm'].some((e) => filename.endsWith(e))) return 'html';
		if (
			[
				'.py',
				'.js',
				'.ts',
				'.jsx',
				'.tsx',
				'.java',
				'.cpp',
				'.c',
				'.h',
				'.rs',
				'.go',
				'.rb',
				'.php',
				'.swift',
				'.kt',
				'.sql',
				'.sh',
				'.bash',
				'.css',
				'.scss',
				'.vue',
				'.svelte'
			].some((e) => filename.endsWith(e))
		)
			return 'code';
		if (['.md'].some((e) => filename.endsWith(e))) return 'markdown';
		return 'text';
	}

	function handleFileSelect(e: Event) {
		const target = e.target as HTMLInputElement;
		if (target.files?.length) {
			const file = target.files[0];
			const type = getFileType(file.name);
			onUploadFile(file, type);
			target.value = '';
			onClose();
		}
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;

		if (e.dataTransfer?.files?.length) {
			const file = e.dataTransfer.files[0];
			const type = getFileType(file.name);
			onUploadFile(file, type);
			onClose();
		}
	}

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		dragOver = true;
	}

	function handleDragLeave() {
		dragOver = false;
	}

	function handleTextSubmit() {
		if (textContent.trim()) {
			onAddText(textContent.trim());
			textContent = '';
			onClose();
		}
	}

	function handleUrlSubmit() {
		if (urlInput.trim() && onAddUrl) {
			onAddUrl(urlInput.trim());
			urlInput = '';
			onClose();
		}
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			onClose();
		}
	}
</script>

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4"
		style="background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px);"
		onclick={handleBackdropClick}
		onkeydown={(e) => e.key === 'Escape' && onClose()}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden"
			style="background-color: var(--background-light); border: 1px solid var(--border);"
			onclick={(e) => e.stopPropagation()}
			role="document"
		>
			<!-- Header -->
			<div
				class="p-4 flex items-center justify-between"
				style="border-bottom: 1px solid var(--border);"
			>
				<h2 class="text-lg font-semibold flex items-center gap-2" style="color: var(--text);">
					<Icon icon="mdi:plus-circle" width="22" style="color: var(--primary);" />
					Add Source
				</h2>
				<button
					onclick={onClose}
					class="p-1 rounded-lg transition-colors hover:opacity-70"
					style="color: var(--text-muted);"
				>
					<Icon icon="mdi:close" width="20" />
				</button>
			</div>

			<!-- Tabs -->
			<div class="flex p-2 gap-1 overflow-x-auto" style="background-color: var(--background);">
				{#each tabs as tab}
					<button
						onclick={() => (activeTab = tab.id)}
						class="flex-1 py-2 px-3 rounded-xl text-xs font-medium flex items-center justify-center gap-1.5 transition-all whitespace-nowrap min-w-fit"
						style="background-color: {activeTab === tab.id
							? 'var(--background-light)'
							: 'transparent'}; 
							   color: {activeTab === tab.id ? tab.color : 'var(--text-muted)'};
							   border: 1px solid {activeTab === tab.id ? 'var(--border)' : 'transparent'};"
					>
						<Icon icon={tab.icon} width="16" />
						{tab.label}
					</button>
				{/each}
			</div>

			<!-- Content -->
			<div class="p-6">
				{#if activeTab === 'text'}
					<!-- Text Input -->
					<div class="space-y-4">
						<div>
							<label
								for="textContent"
								class="block text-sm font-medium mb-2"
								style="color: var(--text);"
							>
								Paste or type your text
							</label>
							<textarea
								id="textContent"
								bind:value={textContent}
								placeholder="Enter your text content here..."
								rows="8"
								class="w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 text-sm resize-none"
								style="background-color: var(--background); border: 1px solid var(--border); color: var(--text); --tw-ring-color: var(--primary);"
							></textarea>
						</div>

						<div class="flex items-center gap-4">
							<div class="flex-1 h-px" style="background-color: var(--border);"></div>
							<span class="text-xs" style="color: var(--text-muted);">or</span>
							<div class="flex-1 h-px" style="background-color: var(--border);"></div>
						</div>

						<button
							onclick={() => fileInput?.click()}
							class="w-full py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors hover:opacity-80"
							style="background-color: var(--background); border: 1px dashed var(--border); color: var(--text-muted);"
						>
							<Icon icon="mdi:file-upload-outline" width="20" />
							Upload .txt or .md file
						</button>

						<button
							onclick={handleTextSubmit}
							disabled={!textContent.trim()}
							class="w-full py-3 rounded-lg text-sm font-medium text-white flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90"
							style="background-color: var(--primary);"
						>
							<Icon icon="mdi:plus" width="20" />
							Add Text Source
						</button>
					</div>
				{:else if activeTab === 'web'}
					<!-- Web URL Input -->
					<div class="space-y-4">
						<div>
							<label
								for="urlInput"
								class="block text-sm font-medium mb-2"
								style="color: var(--text);"
							>
								Website URL
							</label>
							<div class="relative">
								<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
									<Icon icon="mdi:link" width="18" style="color: var(--text-muted);" />
								</div>
								<input
									id="urlInput"
									type="url"
									bind:value={urlInput}
									placeholder="https://example.com/article or https://youtube.com/watch?v=..."
									class="w-full pl-10 pr-4 py-3 rounded-lg focus:outline-none focus:ring-2 text-sm"
									style="background-color: var(--background); border: 1px solid var(--border); color: var(--text); --tw-ring-color: var(--primary);"
									onkeydown={(e) => e.key === 'Enter' && handleUrlSubmit()}
								/>
							</div>
							<p class="mt-2 text-xs" style="color: var(--text-muted);">
								Enter a website URL, YouTube video, or GitHub file link. The content will be
								extracted and added as a source.
							</p>
						</div>

						<button
							onclick={handleUrlSubmit}
							disabled={!urlInput.trim()}
							class="w-full py-3 rounded-lg text-sm font-medium text-white flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90"
							style="background-color: var(--primary);"
						>
							<Icon icon="mdi:plus" width="20" />
							Add Website
						</button>
					</div>
				{:else}
					<!-- File Upload -->
					<div
						class="border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer hover:border-opacity-70"
						style="border-color: {dragOver ? 'var(--primary)' : 'var(--border)'}; 
							   background-color: {dragOver ? 'rgba(99, 102, 241, 0.05)' : 'var(--background)'};"
						ondrop={handleDrop}
						ondragover={handleDragOver}
						ondragleave={handleDragLeave}
						onclick={() => fileInput?.click()}
						onkeydown={(e) => e.key === 'Enter' && fileInput?.click()}
						role="button"
						tabindex="0"
					>
						<div
							class="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
							style="background-color: {currentTab?.color}20;"
						>
							<Icon
								icon={currentFileGroup?.icon || 'mdi:file'}
								width="32"
								style="color: {currentTab?.color};"
							/>
						</div>

						<p class="font-medium mb-1" style="color: var(--text);">Drop your files here</p>
						<p class="text-sm mb-4" style="color: var(--text-muted);">or click to browse</p>

						<div
							class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs"
							style="background-color: var(--background-light); color: var(--text-muted);"
						>
							<Icon icon="mdi:information-outline" width="14" />
							{currentFileGroup?.label}
						</div>
					</div>

					<!-- Supported formats detail -->
					<div class="mt-4 p-3 rounded-lg" style="background-color: var(--background);">
						<p class="text-xs font-medium mb-2" style="color: var(--text-muted);">
							Supported extensions:
						</p>
						<div class="flex flex-wrap gap-1">
							{#each currentFileGroup?.extensions.slice(0, 10) || [] as ext}
								<span
									class="px-2 py-0.5 rounded text-xs"
									style="background-color: {currentTab?.color}15; color: {currentTab?.color};"
								>
									{ext}
								</span>
							{/each}
							{#if (currentFileGroup?.extensions.length || 0) > 10}
								<span
									class="px-2 py-0.5 rounded text-xs"
									style="background-color: var(--background-light); color: var(--text-muted);"
								>
									+{(currentFileGroup?.extensions.length || 0) - 10} more
								</span>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<!-- Hidden file input -->
			<input
				type="file"
				class="hidden"
				bind:this={fileInput}
				onchange={handleFileSelect}
				accept={getAcceptTypes()}
			/>
		</div>
	</div>
{/if}

<style>
	/* Animation for modal */
	div[role='dialog'] > div {
		animation: modalIn 0.2s ease-out;
	}

	@keyframes modalIn {
		from {
			opacity: 0;
			transform: scale(0.95) translateY(-10px);
		}
		to {
			opacity: 1;
			transform: scale(1) translateY(0);
		}
	}
</style>
