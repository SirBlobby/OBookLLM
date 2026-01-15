<script lang="ts">
	import Icon from '@iconify/svelte';
	import { signIn } from '@auth/sveltekit/client';
	import { goto, invalidateAll } from '$app/navigation';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!email.trim() || !password.trim()) {
			error = 'Please fill in all fields';
			return;
		}

		loading = true;
		error = '';

		try {
			const result = await signIn('credentials', {
				email,
				password,
				redirect: false
			});

			if (result?.error) {
				error = 'Invalid email or password';
			} else {
				await invalidateAll();
				goto('/');
			}
		} catch (e) {
			error = 'An error occurred. Please try again.';
		} finally {
			loading = false;
		}
	}
</script>

<div
	class="min-h-screen flex flex-col justify-center py-8 px-4"
	style="background-color: var(--background);"
>
	<div class="w-full max-w-md mx-auto">
		<!-- Logo -->
		<div class="text-center mb-8">
			<div
				class="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4 text-white"
				style="background-color: var(--primary);"
			>
				<Icon icon="mdi:notebook" width="32" />
			</div>
			<h1 class="text-2xl font-bold" style="color: var(--text);">Welcome back</h1>
			<p class="mt-2" style="color: var(--text-muted);">Sign in to your NotebookClone account</p>
		</div>

		<!-- Form Card -->
		<div
			class="rounded-2xl p-8 shadow-lg"
			style="background-color: var(--background-light); border: 1px solid var(--border);"
		>
			<form onsubmit={handleSubmit} class="space-y-5">
				{#if error}
					<div
						class="p-3 rounded-lg text-sm flex items-center gap-2"
						style="background-color: rgba(239, 68, 68, 0.1); color: var(--error);"
					>
						<Icon icon="mdi:alert-circle" width="18" />
						{error}
					</div>
				{/if}

				<div>
					<label for="email" class="block text-sm font-medium mb-2" style="color: var(--text);"
						>Email</label
					>
					<div class="relative">
						<div class="absolute left-3 top-1/2 -translate-y-1/2" style="color: var(--text-muted);">
							<Icon icon="mdi:email" width="20" />
						</div>
						<input
							id="email"
							type="email"
							bind:value={email}
							placeholder="Enter your email"
							class="w-full pl-10 pr-4 py-3 rounded-lg focus:outline-none focus:ring-2 text-sm"
							style="background-color: var(--background); border: 1px solid var(--border); color: var(--text); --tw-ring-color: var(--primary);"
						/>
					</div>
				</div>

				<div>
					<label for="password" class="block text-sm font-medium mb-2" style="color: var(--text);"
						>Password</label
					>
					<div class="relative">
						<div class="absolute left-3 top-1/2 -translate-y-1/2" style="color: var(--text-muted);">
							<Icon icon="mdi:lock" width="20" />
						</div>
						<input
							id="password"
							type="password"
							bind:value={password}
							placeholder="Enter your password"
							class="w-full pl-10 pr-4 py-3 rounded-lg focus:outline-none focus:ring-2 text-sm"
							style="background-color: var(--background); border: 1px solid var(--border); color: var(--text); --tw-ring-color: var(--primary);"
						/>
					</div>
				</div>

				<div class="flex items-center justify-between text-sm">
					<label class="flex items-center gap-2 cursor-pointer">
						<input type="checkbox" class="rounded" style="accent-color: var(--primary);" />
						<span style="color: var(--text-muted);">Remember me</span>
					</label>
					<a href="/forgot-password" style="color: var(--primary);" class="hover:underline"
						>Forgot password?</a
					>
				</div>

				<button
					type="submit"
					disabled={loading}
					class="w-full py-3 rounded-lg font-medium text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
					style="background-color: var(--primary);"
				>
					{#if loading}
						<Icon icon="mdi:loading" class="animate-spin" width="20" />
						Signing in...
					{:else}
						Sign In
					{/if}
				</button>
			</form>

			<div class="mt-6 pt-6" style="border-top: 1px solid var(--border);">
				<p class="text-center text-sm" style="color: var(--text-muted);">
					Don't have an account?
					<a href="/register" style="color: var(--primary);" class="font-medium hover:underline"
						>Create one</a
					>
				</p>
			</div>
		</div>
	</div>
</div>
