<script lang="ts">
	interface Props {
		url: string;
		title?: string;
		onTimeUpdate?: (time: number) => void;
	}

	let { url, title = 'Audio', onTimeUpdate }: Props = $props();
	let audioElement = $state<HTMLAudioElement>();
	let isPlaying = $state(false);
	let currentTime = $state(0);
	let duration = $state(0);
	let volume = $state(1);
	let loading = $state(true);
	let error = $state<string | null>(null);

	function formatTime(seconds: number): string {
		if (!isFinite(seconds)) return '00:00';
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
	}

	function togglePlay() {
		if (!audioElement) return;
		if (isPlaying) {
			audioElement.pause();
		} else {
			audioElement.play();
		}
	}

	function handleTimeUpdate() {
		if (audioElement) {
			currentTime = audioElement.currentTime;
			onTimeUpdate?.(currentTime);
		}
	}

	function handleLoadedMetadata() {
		if (audioElement) {
			duration = audioElement.duration;
			loading = false;
		}
	}

	function handleSeek(e: Event) {
		const target = e.target as HTMLInputElement;
		if (audioElement) {
			audioElement.currentTime = parseFloat(target.value);
		}
	}

	function handleVolumeChange(e: Event) {
		const target = e.target as HTMLInputElement;
		volume = parseFloat(target.value);
		if (audioElement) {
			audioElement.volume = volume;
		}
	}

	function handleError() {
		loading = false;
		error = 'Failed to load audio file';
	}

	function skipBack() {
		if (audioElement) {
			audioElement.currentTime = Math.max(0, audioElement.currentTime - 10);
		}
	}

	function skipForward() {
		if (audioElement) {
			audioElement.currentTime = Math.min(duration, audioElement.currentTime + 10);
		}
	}
</script>

<div
	class="w-full rounded-lg p-3 border border-white/10"
	style="background-color: var(--background-light);"
>
	{#if error}
		<div class="text-red-400 text-center py-2">
			<p class="text-sm">{error}</p>
		</div>
	{:else}
		<audio
			bind:this={audioElement}
			src={url}
			onplay={() => (isPlaying = true)}
			onpause={() => (isPlaying = false)}
			ontimeupdate={handleTimeUpdate}
			onloadedmetadata={handleLoadedMetadata}
			onerror={handleError}
			onended={() => (isPlaying = false)}
		></audio>

		<div class="flex items-center gap-3">
			<button
				onclick={togglePlay}
				disabled={loading}
				class="w-9 h-9 rounded-full bg-purple-600 hover:bg-purple-500 flex items-center justify-center text-white shrink-0 transition-colors disabled:opacity-50"
			>
				{#if loading}
					<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
						></circle>
						<path
							class="opacity-75"
							fill="currentColor"
							d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
						></path>
					</svg>
				{:else if isPlaying}
					<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
						<path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
					</svg>
				{:else}
					<svg class="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
						<path d="M8 5v14l11-7z" />
					</svg>
				{/if}
			</button>

			<span class="text-xs tabular-nums shrink-0" style="color: var(--text-muted);">
				{formatTime(currentTime)}
			</span>

			<div class="flex-1 min-w-0">
				<input
					type="range"
					min="0"
					max={duration || 100}
					value={currentTime}
					oninput={handleSeek}
					class="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-purple-500"
				/>
			</div>

			<span class="text-xs tabular-nums shrink-0" style="color: var(--text-muted);">
				{formatTime(duration)}
			</span>

			<button
				onclick={skipBack}
				class="p-1 rounded hover:bg-white/10 transition-colors"
				style="color: var(--text-muted);"
				title="-10s"
			>
				<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
					<path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z" />
				</svg>
			</button>
			<button
				onclick={skipForward}
				class="p-1 rounded hover:bg-white/10 transition-colors"
				style="color: var(--text-muted);"
				title="+10s"
			>
				<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
					<path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z" />
				</svg>
			</button>

			<div class="flex items-center gap-1 shrink-0">
				<svg
					class="w-3.5 h-3.5"
					style="color: var(--text-muted);"
					fill="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"
					/>
				</svg>
				<input
					type="range"
					min="0"
					max="1"
					step="0.1"
					value={volume}
					oninput={handleVolumeChange}
					class="w-14 h-1 bg-white/10 rounded-full appearance-none cursor-pointer accent-purple-500"
				/>
			</div>
		</div>
	{/if}
</div>
