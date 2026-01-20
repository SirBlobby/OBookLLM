// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			session: {
				user: {
					id: string;
					name: string;
					email: string;
				};
			} | null;
		}
		interface PageData {
			session: {
				user: {
					id: string;
					name: string;
					email: string;
				};
			} | null;
		}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
