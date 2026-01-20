<script lang="ts">
	import Icon from '@iconify/svelte';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { API_BASE_URL } from '$lib/api';

	import { goto } from '$app/navigation';

	type Tab = 'profile' | 'security' | 'developer' | 'models' | 'stats';

	let activeTab = $derived<Tab>(($page.url.searchParams.get('tab') as Tab) || 'profile');

	let session = $derived($page.data.session);
	let name = $state('');
	let email = $state('');

	let loading = $state(false);

	let fetching = $state(true);

	let error = $state('');
	let success = $state('');

	interface OllamaModel {
		name: string;
		size: number;
		modified_at: string;
	}
	interface ProviderInfo {
		name: string;
		configured: boolean;
		capabilities: {
			chat: boolean;
			streaming: boolean;
			embeddings: boolean;
			vision: boolean;
			function_calling: boolean;
		};
		available_chat_models: string[];
		available_embedding_models: string[];
	}

	let availableModels = $state<OllamaModel[]>([]);
	let providers = $state<Record<string, ProviderInfo>>({});
	let chatProvider = $state('ollama');
	let chatModel = $state('');
	let embeddingProvider = $state('ollama');
	let embeddingModel = $state('');
	let ollamaUrl = $state('http://ollama:11434');
	let pulling = $state(false);
	let newModelName = $state('');
	let apiKeysConfigured = $state<Record<string, boolean>>({});

	let newApiKeyProvider = $state('');
	let newApiKeyValue = $state('');

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');

	let apiKeys = $state<any[]>([]);
	let webhooks = $state<any[]>([]);
	let newKeyName = $state('');
	let newWebhookUrl = $state('');
	let createdApiKey = $state('');

	let statsData = $state<any>(null);
	let canvas1 = $state<HTMLCanvasElement>();
	let canvas2 = $state<HTMLCanvasElement>();
	let canvas3 = $state<HTMLCanvasElement>();
	let Chart: any;

	let chart1: any = null;
	let chart2: any = null;
	let chart3: any = null;

	$effect(() => {
		if (activeTab === 'developer') {
			fetchApiKeys();
			fetchWebhooks();
		}
		if (activeTab === 'stats') {
			fetchStats();
		}
	});

	$effect(() => {
		if (activeTab === 'stats' && canvas1 && statsData?.history && Chart) {
			initCharts();
		}
	});

	onMount(async () => {
		fetchSettings();
		if (session?.user) {
			name = session.user.name || '';
			email = session.user.email || '';
		}

		const mod = await import('chart.js/auto');
		Chart = mod.default;
	});

	function switchTab(t: Tab) {
		goto(`?tab=${t}`, { replaceState: true, keepFocus: true, noScroll: true });
		error = '';
		success = '';
	}

	async function fetchStats() {
		try {
			const res = await fetch(`${API_BASE_URL}/stats`);
			if (res.ok) statsData = await res.json();
		} catch (e) {
			console.error(e);
		}
	}

	function createChartConfig(
		ctx: HTMLCanvasElement,
		label: string,
		data: number[],
		labels: string[],
		color: string
	) {
		if (!Chart) return;
		return new Chart(ctx, {
			type: 'line',
			data: {
				labels: [...labels],
				datasets: [
					{
						label: label,
						data: [...data],
						backgroundColor: color.replace(')', ', 0.15)').replace('rgb', 'rgba'),
						borderColor: color,
						borderWidth: 2,
						tension: 0.4,
						fill: true,
						pointBackgroundColor: '#fff',
						pointBorderColor: color,
						pointRadius: 4,
						pointHoverRadius: 6
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false } },
				scales: {
					y: {
						beginAtZero: true,
						grid: { color: 'rgba(255,255,255,0.05)' },
						border: { display: false }
					},
					x: { grid: { display: false }, border: { display: false }, ticks: { maxTicksLimit: 6 } }
				},
				interaction: { mode: 'index', intersect: false }
			}
		});
	}

	function initCharts() {
		if (!statsData?.history || !Chart) return;

		if (chart1) chart1.destroy();
		if (chart2) chart2.destroy();
		if (chart3) chart3.destroy();

		const formattedLabels = statsData.history.labels.map((l: string) => {
			if (l === 'Start') return '';
			const d = new Date(l);
			return isNaN(d.getTime())
				? l
				: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
		});

		if (canvas1)
			chart1 = createChartConfig(
				canvas1,
				'Notebooks Created',
				statsData.history.notebooks,
				formattedLabels,
				'rgb(99, 102, 241)'
			);
		if (canvas2)
			chart2 = createChartConfig(
				canvas2,
				'Sources Uploaded',
				statsData.history.sources,
				formattedLabels,
				'rgb(16, 185, 129)'
			);
		if (canvas3)
			chart3 = createChartConfig(
				canvas3,
				'API Requests',
				statsData.history.api_requests,
				formattedLabels,
				'rgb(245, 158, 11)'
			);
	}

	function findMatchingModel(modelName: string): OllamaModel | undefined {
		let match = availableModels.find((m) => m.name === modelName);
		if (match) return match;
		match = availableModels.find((m) => m.name === `${modelName}:latest`);
		if (match) return match;
		const baseName = modelName.replace(/:latest$/, '');
		return availableModels.find((m) => m.name === baseName || m.name === `${baseName}:latest`);
	}
	function isModelInstalled(modelName: string): boolean {
		return findMatchingModel(modelName) !== undefined;
	}
	function formatSize(bytes: number): string {
		if (bytes === 0) return 'Unknown';
		const gb = bytes / (1024 * 1024 * 1024);
		if (gb >= 1) return `${gb.toFixed(1)} GB`;
		const mb = bytes / (1024 * 1024);
		return `${mb.toFixed(0)} MB`;
	}

	async function fetchSettings() {
		fetching = true;
		try {
			const [settingsRes, modelsRes] = await Promise.all([
				fetch(`${API_BASE_URL}/settings`),
				fetch(`${API_BASE_URL}/settings/models`)
			]);
			if (modelsRes.ok) availableModels = (await modelsRes.json()).models;
			if (settingsRes.ok) {
				const s = await settingsRes.json();

				if (s.providers) providers = s.providers;
				if (s.api_keys_configured) apiKeysConfigured = s.api_keys_configured;

				chatProvider = s.chat_provider || 'ollama';
				embeddingProvider = s.embedding_provider || 'ollama';
				ollamaUrl = s.ollama_url || 'http://ollama:11434';

				const chatMatch = findMatchingModel(s.chat_model);
				const embedMatch = findMatchingModel(s.embedding_model);
				chatModel = chatMatch?.name || s.chat_model;
				embeddingModel = embedMatch?.name || s.embedding_model;
			}
		} catch (e) {
			console.error(e);
		} finally {
			fetching = false;
		}
	}

	async function saveSettings() {
		loading = true;
		error = '';
		success = '';
		try {
			const res = await fetch(`${API_BASE_URL}/settings`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					chat_provider: chatProvider,
					chat_model: chatModel,
					embedding_provider: embeddingProvider,
					embedding_model: embeddingModel,
					ollama_url: ollamaUrl
				})
			});
			if (res.ok) {
				success = 'Settings saved successfully!';
				fetchSettings();
			} else {
				error = (await res.json()).detail || 'Failed';
			}
		} catch (e) {
			error = 'Network error';
		} finally {
			loading = false;
		}
	}

	async function saveApiKey() {
		if (!newApiKeyProvider || !newApiKeyValue) return;
		loading = true;
		error = '';
		try {
			const res = await fetch(`${API_BASE_URL}/settings/api-keys`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ provider: newApiKeyProvider, api_key: newApiKeyValue })
			});
			if (res.ok) {
				success = `API key for ${newApiKeyProvider} saved!`;
				newApiKeyProvider = '';
				newApiKeyValue = '';
				fetchSettings();
			} else {
				error = (await res.json()).detail || 'Failed to save API key';
			}
		} catch (e) {
			error = 'Network error';
		} finally {
			loading = false;
		}
	}

	async function removeApiKey(provider: string) {
		if (!confirm(`Remove API key for ${provider}?`)) return;
		try {
			await fetch(`${API_BASE_URL}/settings/api-keys/${provider}`, { method: 'DELETE' });
			fetchSettings();
		} catch (e) {
			console.error(e);
		}
	}

	function getProviderModels(provider: string, type: 'chat' | 'embedding'): string[] {
		const p = providers[provider];
		if (!p) return [];
		return type === 'chat' ? p.available_chat_models : p.available_embedding_models;
	}

	async function pullModel() {
		if (!newModelName.trim()) return;
		pulling = true;
		error = '';
		success = '';
		try {
			const res = await fetch(`${API_BASE_URL}/settings`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ chat_model: newModelName.trim(), embedding_model: embeddingModel })
			});
			if (res.ok) {
				success = `Model "${newModelName}" pulled successfully!`;
				chatModel = newModelName.trim();
				newModelName = '';
				fetchSettings();
			} else {
				error = (await res.json()).detail || 'Failed';
			}
		} catch (e) {
			error = 'Network error';
		} finally {
			pulling = false;
		}
	}

	async function saveProfile() {
		if (!email) return;
		loading = true;
		error = '';
		success = '';
		try {
			const res = await fetch(`${API_BASE_URL}/auth/profile`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, name })
			});
			if (res.ok) success = 'Profile updated successfully!';
			else error = (await res.json()).detail || 'Failed';
		} catch (e) {
			error = 'Network error';
		} finally {
			loading = false;
		}
	}

	async function changePassword() {
		if (!currentPassword || !newPassword || !confirmPassword) {
			error = 'Fill all fields';
			return;
		}
		if (newPassword !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}
		loading = true;
		error = '';
		success = '';
		try {
			const res = await fetch(`${API_BASE_URL}/auth/password`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					email,
					current_password: currentPassword,
					new_password: newPassword
				})
			});
			if (res.ok) {
				success = 'Password changed!';
				currentPassword = '';
				newPassword = '';
				confirmPassword = '';
			} else error = (await res.json()).detail || 'Failed';
		} catch (e) {
			error = 'Network error';
		} finally {
			loading = false;
		}
	}

	async function fetchApiKeys() {
		const res = await fetch(
			`${API_BASE_URL}/auth/api-keys?email=${encodeURIComponent(email)}`
		);
		if (res.ok) apiKeys = (await res.json()).keys;
	}
	async function createApiKey() {
		if (!newKeyName) return;
		const res = await fetch(`${API_BASE_URL}/auth/api-keys`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email, name: newKeyName })
		});
		if (res.ok) {
			const d = await res.json();
			createdApiKey = d.key;
			newKeyName = '';
			fetchApiKeys();
		}
	}
	async function deleteApiKey(id: string) {
		if (!confirm('Delete key?')) return;
		await fetch(`${API_BASE_URL}/auth/api-keys/${id}`, { method: 'DELETE' });
		fetchApiKeys();
	}

	async function fetchWebhooks() {
		const res = await fetch(
			`${API_BASE_URL}/auth/webhooks?email=${encodeURIComponent(email)}`
		);
		if (res.ok) webhooks = (await res.json()).webhooks;
	}
	async function createWebhook() {
		if (!newWebhookUrl) return;
		const res = await fetch(`${API_BASE_URL}/auth/webhooks`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email, url: newWebhookUrl, events: ['all'] })
		});
		if (res.ok) {
			newWebhookUrl = '';
			fetchWebhooks();
		}
	}
	async function deleteWebhook(id: string) {
		if (!confirm('Delete webhook?')) return;
		await fetch(`${API_BASE_URL}/auth/webhooks/${id}`, { method: 'DELETE' });
		fetchWebhooks();
	}
</script>

<div class="h-full overflow-y-auto relative z-10">
	<div class="p-8 max-w-6xl mx-auto w-full pb-16">
		<header class="mb-8">
			<h1 class="text-2xl font-bold flex items-center gap-3" style="color: var(--text);">
				<Icon icon="mdi:cog" width="28" />
				Settings
			</h1>
			<p class="mt-2" style="color: var(--text-muted);">Manage your account and AI preferences</p>
		</header>

		<div class="flex gap-2 mb-6 border-b" style="border-color: var(--border);">
			{#each [{ id: 'profile', label: 'Profile', icon: 'mdi:account' }, { id: 'security', label: 'Security', icon: 'mdi:shield-lock' }, { id: 'developer', label: 'Developer', icon: 'mdi:code-braces' }, { id: 'models', label: 'AI Models', icon: 'mdi:robot' }, { id: 'stats', label: 'Stats', icon: 'mdi:chart-bar' }] as tab}
				<button
					type="button"
					class="px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2"
					style="border-color: {activeTab === tab.id
						? 'var(--primary)'
						: 'transparent'}; color: {activeTab === tab.id ? 'var(--text)' : 'var(--text-muted)'};"
					onclick={() => switchTab(tab.id as Tab)}
				>
					<Icon icon={tab.icon} width="18" />
					{tab.label}
				</button>
			{/each}
		</div>

		{#if error}
			<div
				class="mb-6 p-4 rounded flex items-center gap-2 border border-red-500/20"
				style="background-color: rgba(239, 68, 68, 0.1); color: var(--error);"
			>
				<Icon icon="mdi:alert-circle" width="20" />
				{error}
			</div>
		{/if}
		{#if success}
			<div
				class="mb-6 p-4 rounded flex items-center gap-2 border border-green-500/20"
				style="background-color: rgba(34, 197, 94, 0.1); color: #22c55e;"
			>
				<Icon icon="mdi:check-circle" width="20" />
				{success}
			</div>
		{/if}

		<div
			class="rounded p-6 border"
			style="background-color: var(--background-light); border-color: var(--border);"
		>
			{#if activeTab === 'profile'}
				{#if !session?.user}
					<p class="text-center py-4" style="color: var(--text-muted);">
						Please sign in to edit profile.
					</p>
				{:else}
					<div class="space-y-6">
						<div class="flex items-center gap-4">
							<div
								class="w-16 h-16 rounded bg-primary flex items-center justify-center text-white font-bold text-xl uppercase"
							>
								{name?.[0] || email?.[0] || 'U'}
							</div>
							<div>
								<h3 class="font-semibold text-lg" style="color: var(--text);">{name || 'User'}</h3>
								<p class="text-sm" style="color: var(--text-muted);">{email}</p>
							</div>
						</div>
						<div class="grid gap-4 max-w-lg">
							<div>
								<label for="name" class="block text-sm font-medium mb-1" style="color: var(--text);"
									>Full Name</label
								>
								<input
									id="name"
									type="text"
									bind:value={name}
									class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border"
									style="background-color: var(--background); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
								/>
							</div>
							<div>
								<label
									for="email"
									class="block text-sm font-medium mb-1"
									style="color: var(--text);">Email</label
								>
								<input
									id="email"
									type="text"
									value={email}
									disabled
									class="w-full px-4 py-2 rounded opacity-50 cursor-not-allowed text-sm border"
									style="background-color: var(--background); border-color: var(--border); color: var(--text);"
								/>
							</div>
							<button
								type="button"
								onclick={saveProfile}
								disabled={loading}
								class="w-full sm:w-auto px-5 py-2 rounded font-medium text-white bg-primary disabled:opacity-50 flex items-center justify-center gap-2"
							>
								<Icon
									icon={loading ? 'mdi:loading' : 'mdi:content-save'}
									class={loading ? 'animate-spin' : ''}
									width="18"
								/> Save Profile
							</button>
						</div>
					</div>
				{/if}
			{:else if activeTab === 'security'}
				{#if !session?.user}
					<p class="text-center py-4" style="color: var(--text-muted);">
						Please sign in to manage security.
					</p>
				{:else}
					<div class="space-y-4 max-w-md">
						<h3 class="font-semibold" style="color: var(--text);">Change Password</h3>
						<input
							type="password"
							bind:value={currentPassword}
							placeholder="Current Password"
							class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border"
							style="background-color: var(--background); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
						/>
						<input
							type="password"
							bind:value={newPassword}
							placeholder="New Password"
							class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border"
							style="background-color: var(--background); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
						/>
						<input
							type="password"
							bind:value={confirmPassword}
							placeholder="Confirm New Password"
							class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border"
							style="background-color: var(--background); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
						/>
						<button
							type="button"
							onclick={changePassword}
							disabled={loading}
							class="w-full sm:w-auto px-5 py-2 rounded font-medium text-white bg-primary disabled:opacity-50 flex items-center justify-center gap-2"
						>
							<Icon
								icon={loading ? 'mdi:loading' : 'mdi:lock-reset'}
								class={loading ? 'animate-spin' : ''}
								width="18"
							/> Update Password
						</button>
					</div>
				{/if}
			{:else if activeTab === 'developer'}
				{#if !session?.user}
					<p class="text-center py-4" style="color: var(--text-muted);">
						Please sign in to view developer settings.
					</p>
				{:else}
					<div class="space-y-8">
						<div>
							<h3 class="font-semibold mb-3 flex items-center gap-2" style="color: var(--text);">
								<Icon icon="mdi:key-variant" /> API Keys
							</h3>
							{#if createdApiKey}
								<div class="p-3 rounded border border-green-500/50 bg-green-500/10 mb-4">
									<p class="text-xs font-bold text-green-500 mb-1">New Key Created!</p>
									<div
										class="flex items-center gap-2 bg-black/20 p-2 rounded font-mono text-sm break-all"
									>
										{createdApiKey}
										<button
											type="button"
											class="ml-auto text-xs hover:text-white"
											onclick={() => navigator.clipboard.writeText(createdApiKey)}>Copy</button
										>
									</div>
									<button
										type="button"
										onclick={() => (createdApiKey = '')}
										class="text-xs underline mt-2">Dismiss</button
									>
								</div>
							{/if}
							<div class="flex gap-2 mb-3">
								<input
									type="text"
									bind:value={newKeyName}
									placeholder="Key Name"
									class="flex-1 px-3 py-2 rounded text-sm border"
									style="background-color: var(--background); border-color: var(--border); color: var(--text);"
								/>
								<button
									type="button"
									onclick={createApiKey}
									disabled={!newKeyName}
									class="px-3 py-2 rounded text-white bg-primary text-sm font-medium disabled:opacity-50"
									>Create</button
								>
							</div>
							<div class="space-y-2">
								{#each apiKeys as key}
									<div
										class="flex items-center justify-between p-3 rounded border"
										style="border-color: var(--border); background-color: var(--background);"
									>
										<div>
											<div class="font-medium text-sm" style="color: var(--text);">{key.name}</div>
											<div class="text-xs font-mono opacity-60" style="color: var(--text-muted);">
												{key.prefix}
											</div>
										</div>
										<button
											type="button"
											onclick={() => deleteApiKey(key.id)}
											class="text-red-500 p-1 hover:bg-red-500/10 rounded"
											><Icon icon="mdi:trash-can-outline" width="18" /></button
										>
									</div>
								{/each}
								{#if apiKeys.length === 0}
									<div class="text-sm opacity-50 text-center py-2">No API keys</div>
								{/if}
							</div>
						</div>

						<div>
							<h3 class="font-semibold mb-3 flex items-center gap-2" style="color: var(--text);">
								<Icon icon="mdi:webhook" /> Webhooks
							</h3>
							<div class="flex gap-2 mb-3">
								<input
									type="text"
									bind:value={newWebhookUrl}
									placeholder="https://..."
									class="flex-1 px-3 py-2 rounded text-sm border"
									style="background-color: var(--background); border-color: var(--border); color: var(--text);"
								/>
								<button
									type="button"
									onclick={createWebhook}
									disabled={!newWebhookUrl}
									class="px-3 py-2 rounded text-white bg-primary text-sm font-medium disabled:opacity-50"
									>Add</button
								>
							</div>
							<div class="space-y-2">
								{#each webhooks as hook}
									<div
										class="flex items-center justify-between p-3 rounded border"
										style="border-color: var(--border); background-color: var(--background);"
									>
										<div class="truncate flex-1 mr-4">
											<div class="font-mono text-xs" style="color: var(--text);">{hook.url}</div>
										</div>
										<button
											type="button"
											onclick={() => deleteWebhook(hook.id)}
											class="text-red-500 p-1 hover:bg-red-500/10 rounded"
											><Icon icon="mdi:trash-can-outline" width="18" /></button
										>
									</div>
								{/each}
								{#if webhooks.length === 0}
									<div class="text-sm opacity-50 text-center py-2">No webhooks</div>
								{/if}
							</div>
						</div>
					</div>
				{/if}
			{:else if activeTab === 'stats'}
				{#if !statsData}
					<div class="py-12 flex justify-center">
						<Icon icon="mdi:loading" class="animate-spin text-primary" width="32" />
					</div>
				{:else}
					<div class="space-y-6">
						<div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
							<div
								class="p-4 rounded border"
								style="border-color: var(--border); background-color: var(--background);"
							>
								<div
									class="text-xs uppercase font-bold opacity-60 mb-1"
									style="color: var(--text-muted);"
								>
									Tokens (Est.)
								</div>
								<div class="text-2xl font-bold" style="color: var(--text);">
									{statsData.tokens.toLocaleString()}
								</div>
							</div>
							<div
								class="p-4 rounded border"
								style="border-color: var(--border); background-color: var(--background);"
							>
								<div
									class="text-xs uppercase font-bold opacity-60 mb-1"
									style="color: var(--text-muted);"
								>
									Storage Used
								</div>
								<div class="text-2xl font-bold" style="color: var(--text);">
									{formatSize(statsData.storage_bytes)}
								</div>
							</div>
							<div
								class="p-4 rounded border"
								style="border-color: var(--border); background-color: var(--background);"
							>
								<div
									class="text-xs uppercase font-bold opacity-60 mb-1"
									style="color: var(--text-muted);"
								>
									API Requests
								</div>
								<div class="text-2xl font-bold" style="color: var(--text);">
									{statsData.api_requests}
								</div>
							</div>
							<div
								class="p-4 rounded border"
								style="border-color: var(--border); background-color: var(--background);"
							>
								<div
									class="text-xs uppercase font-bold opacity-60 mb-1"
									style="color: var(--text-muted);"
								>
									Notebooks
								</div>
								<div class="text-2xl font-bold" style="color: var(--text);">
									{statsData.notebooks}
								</div>
							</div>
							<div
								class="p-4 rounded border"
								style="border-color: var(--border); background-color: var(--background);"
							>
								<div
									class="text-xs uppercase font-bold opacity-60 mb-1"
									style="color: var(--text-muted);"
								>
									Sources
								</div>
								<div class="text-2xl font-bold" style="color: var(--text);">
									{statsData.sources}
								</div>
							</div>
						</div>

						<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
							<div
								class="p-4 rounded border"
								style="border-color: var(--border); background-color: var(--background);"
							>
								<h3 class="text-sm font-semibold mb-4" style="color: var(--text-muted)">
									Notebooks Created
								</h3>
								<div class="h-48 relative w-full">
									<canvas bind:this={canvas1} class="w-full h-full"></canvas>
								</div>
							</div>

							<div
								class="p-4 rounded border"
								style="border-color: var(--border); background-color: var(--background);"
							>
								<h3 class="text-sm font-semibold mb-4" style="color: var(--text-muted)">
									Sources Uploaded
								</h3>
								<div class="h-48 relative w-full">
									<canvas bind:this={canvas2} class="w-full h-full"></canvas>
								</div>
							</div>

							<div
								class="p-4 rounded border lg:col-span-2"
								style="border-color: var(--border); background-color: var(--background);"
							>
								<h3 class="text-sm font-semibold mb-4" style="color: var(--text-muted)">
									API Interaction Activity
								</h3>
								<div class="h-48 relative w-full">
									<canvas bind:this={canvas3} class="w-full h-full"></canvas>
								</div>
							</div>
						</div>
					</div>
				{/if}
			{:else if activeTab === 'models'}
				{#if fetching}
					<div class="flex flex-col items-center justify-center py-12 opacity-50">
						<Icon
							icon="mdi:loading"
							class="animate-spin mb-4"
							width="32"
							style="color: var(--primary);"
						/>
						<p class="text-sm">Loading models...</p>
					</div>
				{:else}
					<div class="space-y-6">
						<div>
							<h3 class="font-semibold mb-3 flex items-center gap-2" style="color: var(--text);">
								<Icon icon="mdi:cloud-outline" /> AI Providers
							</h3>
							<p class="text-sm mb-4" style="color: var(--text-muted);">
								Select which AI provider to use for chat and embeddings. Ollama runs locally, while
								others require API keys.
							</p>

							<div class="grid gap-4 md:grid-cols-2">
								<div
									class="p-4 rounded border"
									style="border-color: var(--border); background-color: var(--background);"
								>
									<label
										for="chatProvider"
										class="block text-sm font-medium mb-2"
										style="color: var(--text);"
									>
										Chat Provider
									</label>
									<select
										id="chatProvider"
										bind:value={chatProvider}
										class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border mb-3"
										style="background-color: var(--background-light); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
									>
										<option value="ollama">🏠 Ollama (Local)</option>
										<option value="openai">🟢 OpenAI</option>
										<option value="anthropic">🟣 Anthropic (Claude)</option>
										<option value="gemini">🔵 Google Gemini</option>
									</select>

									<label
										for="chatModel"
										class="block text-sm font-medium mb-1"
										style="color: var(--text);"
									>
										Chat Model
									</label>
									{#if chatProvider === 'ollama'}
										<select
											id="chatModel"
											bind:value={chatModel}
											class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border"
											style="background-color: var(--background-light); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
										>
											{#each availableModels as model}
												<option value={model.name}>{model.name} ({formatSize(model.size)})</option>
											{/each}
											{#if !isModelInstalled(chatModel) && chatModel}
												<option value={chatModel}>{chatModel} (not installed)</option>
											{/if}
										</select>
									{:else}
										<select
											id="chatModel"
											bind:value={chatModel}
											class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border"
											style="background-color: var(--background-light); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
										>
											{#each getProviderModels(chatProvider, 'chat') as model}
												<option value={model}>{model}</option>
											{/each}
										</select>
									{/if}

									{#if chatProvider !== 'ollama' && !apiKeysConfigured[chatProvider]}
										<p class="text-xs mt-2 text-yellow-500 flex items-center gap-1">
											<Icon icon="mdi:alert" width="14" /> API key required
										</p>
									{/if}
								</div>

								<div
									class="p-4 rounded border"
									style="border-color: var(--border); background-color: var(--background);"
								>
									<label
										for="embeddingProvider"
										class="block text-sm font-medium mb-2"
										style="color: var(--text);"
									>
										Embedding Provider
									</label>
									<select
										id="embeddingProvider"
										bind:value={embeddingProvider}
										class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border mb-3"
										style="background-color: var(--background-light); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
									>
										<option value="ollama">🏠 Ollama (Local)</option>
										<option value="openai">🟢 OpenAI</option>
										<option value="gemini">🔵 Google Gemini</option>
										<!-- Anthropic doesn't support embeddings -->
									</select>

									<label
										for="embeddingModel"
										class="block text-sm font-medium mb-1"
										style="color: var(--text);"
									>
										Embedding Model
									</label>
									{#if embeddingProvider === 'ollama'}
										<select
											id="embeddingModel"
											bind:value={embeddingModel}
											class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border"
											style="background-color: var(--background-light); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
										>
											{#each availableModels as model}
												<option value={model.name}>{model.name} ({formatSize(model.size)})</option>
											{/each}
											{#if !isModelInstalled(embeddingModel) && embeddingModel}
												<option value={embeddingModel}>{embeddingModel} (not installed)</option>
											{/if}
										</select>
									{:else}
										<select
											id="embeddingModel"
											bind:value={embeddingModel}
											class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border"
											style="background-color: var(--background-light); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
										>
											{#each getProviderModels(embeddingProvider, 'embedding') as model}
												<option value={model}>{model}</option>
											{/each}
										</select>
									{/if}

									{#if embeddingProvider !== 'ollama' && !apiKeysConfigured[embeddingProvider]}
										<p class="text-xs mt-2 text-yellow-500 flex items-center gap-1">
											<Icon icon="mdi:alert" width="14" /> API key required
										</p>
									{/if}
								</div>
							</div>

							{#if chatProvider === 'ollama' || embeddingProvider === 'ollama'}
								<div
									class="p-4 rounded border mt-4"
									style="border-color: var(--border); background-color: var(--background);"
								>
									<label
										for="ollamaUrl"
										class="block text-sm font-medium mb-2"
										style="color: var(--text);"
									>
										<Icon icon="mdi:server-network" class="inline mr-1" /> Ollama Server URL
									</label>
									<input
										id="ollamaUrl"
										type="text"
										bind:value={ollamaUrl}
										placeholder="http://localhost:11434"
										class="w-full px-4 py-2 rounded focus:outline-none focus:ring-2 text-sm border"
										style="background-color: var(--background-light); border-color: var(--border); color: var(--text); --tw-ring-color: var(--primary);"
									/>
									<p class="text-xs mt-2" style="color: var(--text-muted);">
										URL of your Ollama instance. Use <code>http://ollama:11434</code> for Docker or
										<code>http://localhost:11434</code> for local.
									</p>
								</div>
							{/if}

							<button
								type="button"
								onclick={saveSettings}
								disabled={loading}
								class="mt-4 px-5 py-2 rounded font-medium text-white bg-primary disabled:opacity-50 flex items-center gap-2"
							>
								<Icon
									icon={loading ? 'mdi:loading' : 'mdi:content-save'}
									class={loading ? 'animate-spin' : ''}
									width="18"
								/> Save Settings
							</button>
						</div>

						<div class="pt-6 border-t" style="border-color: var(--border);">
							<h3 class="font-semibold mb-3 flex items-center gap-2" style="color: var(--text);">
								<Icon icon="mdi:key" /> API Keys
							</h3>
							<p class="text-sm mb-4" style="color: var(--text-muted);">
								Configure API keys for cloud AI providers. Keys are stored securely.
							</p>

							<div class="grid gap-2 mb-4">
								{#each ['openai', 'anthropic', 'gemini'] as provider}
									<div
										class="flex items-center justify-between px-3 py-2 rounded border"
										style="border-color: var(--border); background-color: var(--background);"
									>
										<div class="flex items-center gap-2">
											<Icon
												icon={provider === 'openai'
													? 'simple-icons:openai'
													: provider === 'anthropic'
														? 'simple-icons:anthropic'
														: 'ri:google-fill'}
												style="color: var(--text);"
											/>
											<span class="capitalize" style="color: var(--text);">{provider}</span>
										</div>
										<div class="flex items-center gap-2">
											{#if apiKeysConfigured[provider]}
												<span class="text-xs px-2 py-1 rounded bg-green-900/30 text-green-400"
													>Configured</span
												>
												<button
													onclick={() => removeApiKey(provider)}
													class="text-red-400 hover:text-red-300"
												>
													<Icon icon="mdi:delete" width="18" />
												</button>
											{:else}
												<span class="text-xs px-2 py-1 rounded bg-gray-700 text-gray-400"
													>Not set</span
												>
											{/if}
										</div>
									</div>
								{/each}
							</div>

							<div class="flex gap-2 items-end">
								<div class="flex-1">
									<label
										for="newApiKeyProvider"
										class="block text-sm mb-1"
										style="color: var(--text-muted);">Provider</label
									>
									<select
										id="newApiKeyProvider"
										bind:value={newApiKeyProvider}
										class="w-full px-3 py-2 rounded text-sm border"
										style="background-color: var(--background); border-color: var(--border); color: var(--text);"
									>
										<option value="">Select provider...</option>
										<option value="openai">OpenAI</option>
										<option value="anthropic">Anthropic</option>
										<option value="gemini">Google Gemini</option>
									</select>
								</div>
								<div class="flex-2">
									<label
										for="newApiKeyValue"
										class="block text-sm mb-1"
										style="color: var(--text-muted);">API Key</label
									>
									<input
										id="newApiKeyValue"
										type="password"
										bind:value={newApiKeyValue}
										placeholder="sk-... or AIza..."
										class="w-full px-3 py-2 rounded text-sm border"
										style="background-color: var(--background); border-color: var(--border); color: var(--text);"
									/>
								</div>
								<button
									type="button"
									onclick={saveApiKey}
									disabled={!newApiKeyProvider || !newApiKeyValue || loading}
									class="px-4 py-2 rounded font-medium text-white bg-primary disabled:opacity-50"
								>
									Save
								</button>
							</div>
						</div>

						{#if chatProvider === 'ollama' || embeddingProvider === 'ollama'}
							<div class="pt-6 border-t" style="border-color: var(--border);">
								<h3 class="font-semibold mb-3 flex items-center gap-2" style="color: var(--text);">
									<Icon icon="mdi:download" /> Pull Ollama Model
								</h3>
								<div class="flex gap-2">
									<input
										type="text"
										bind:value={newModelName}
										placeholder="e.g. llama3, mistral"
										class="flex-1 px-4 py-2 rounded text-sm border"
										style="background-color: var(--background); border-color: var(--border); color: var(--text);"
									/>
									<button
										type="button"
										onclick={pullModel}
										disabled={pulling || !newModelName}
										class="px-5 py-2 rounded font-medium text-white bg-primary disabled:opacity-50 flex items-center gap-2"
									>
										<Icon
											icon={pulling ? 'mdi:loading' : 'mdi:download'}
											class={pulling ? 'animate-spin' : ''}
											width="18"
										/> Pull
									</button>
								</div>
							</div>
						{/if}

						{#if availableModels.length > 0}
							<div class="pt-6 border-t" style="border-color: var(--border);">
								<h3 class="font-semibold mb-3 flex items-center gap-2" style="color: var(--text);">
									<Icon icon="mdi:format-list-bulleted" /> Installed Ollama Models
								</h3>
								<div class="space-y-2">
									{#each availableModels as model}
										<div
											class="flex items-center justify-between px-3 py-2 rounded border"
											style="border-color: var(--border); background-color: var(--background);"
										>
											<div class="flex items-center gap-2">
												<Icon icon="mdi:cube-outline" class="text-primary" /><span
													style="color: var(--text);">{model.name}</span
												>
											</div>
											<span class="text-xs" style="color: var(--text-muted);"
												>{formatSize(model.size)}</span
											>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>

<style>
	select {
		appearance: none;
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 12px center;
		padding-right: 36px;
	}
	select option {
		background-color: #1a1a2e;
		color: #e5e5e5;
		padding: 8px;
	}
</style>
