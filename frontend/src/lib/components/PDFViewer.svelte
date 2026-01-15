<script lang="ts">
	import { onMount, tick } from 'svelte';
	import type * as PDFJS from 'pdfjs-dist';
	import 'pdfjs-dist/web/pdf_viewer.css';

	interface Props {
		url: string;
	}

	let { url }: Props = $props();
	let container = $state<HTMLDivElement>();
	let canvasContainer = $state<HTMLDivElement>();
	let loading = $state(true);
	let error = $state<string | null>(null);
	let pdfDoc: PDFJS.PDFDocumentProxy | null = null;

	onMount(async () => {
		console.log('[PDFViewer] onMount called, url:', url);
		try {
			const pdfjs = await import('pdfjs-dist');
			console.log('[PDFViewer] pdfjs imported, version:', pdfjs.version);
			// Set worker
			// Use a CDN for the worker to avoid complex build setup issues for now,
			// or try to resolve it from node_modules if Vite is configured.
			// Using unpkg matching the installed version is safest for quick integration.
			pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

			loading = true;
			console.log('[PDFViewer] Loading document...');
			const loadingTask = pdfjs.getDocument(url);
			pdfDoc = await loadingTask.promise;
			console.log('[PDFViewer] Document loaded, pages:', pdfDoc.numPages);

			loading = false;
			await tick(); // Wait for DOM to update so canvasContainer is available
			renderPages();
		} catch (e: any) {
			console.error('[PDFViewer] Error loading PDF:', e);
			loading = false;
			error = e.message || 'Failed to load PDF';
		}
	});

	async function renderPages() {
		console.log('[PDFViewer] renderPages called', {
			pdfDoc: !!pdfDoc,
			canvasContainer: !!canvasContainer
		});
		if (!pdfDoc || !canvasContainer) {
			console.log('[PDFViewer] renderPages early return - missing:', {
				pdfDoc: !pdfDoc,
				canvasContainer: !canvasContainer
			});
			return;
		}

		// Clear container
		canvasContainer.innerHTML = '';

		const numPages = pdfDoc.numPages;
		console.log('[PDFViewer] Rendering', numPages, 'pages');
		for (let i = 1; i <= numPages; i++) {
			const page = await pdfDoc.getPage(i);

			// Create wrapper
			const wrapper = document.createElement('div');
			wrapper.className = 'mb-4 shadow-md';
			canvasContainer.appendChild(wrapper);

			// Create canvas
			const canvas = document.createElement('canvas');
			wrapper.appendChild(canvas);

			// Adjust scale
			const viewport = page.getViewport({ scale: 1.5 });
			canvas.height = viewport.height;
			canvas.width = viewport.width;
			canvas.style.width = '100%';
			canvas.style.height = 'auto';

			const renderContext = {
				canvasContext: canvas.getContext('2d')!,
				viewport: viewport
			};
			await page.render(renderContext as any).promise;
		}
	}
</script>

<div class="w-full h-full overflow-y-auto bg-gray-100 p-4" bind:this={container}>
	{#if loading}
		<div class="flex items-center justify-center h-64">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
			<span class="ml-2">Loading PDF...</span>
		</div>
	{:else if error}
		<div class="text-red-500 p-4 text-center">
			<p class="font-bold">Error loading document</p>
			<p>{error}</p>
		</div>
	{:else}
		<div bind:this={canvasContainer} class="max-w-3xl mx-auto"></div>
	{/if}
</div>
