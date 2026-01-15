import { writable } from 'svelte/store';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

export interface Notebook {
    id: string;
    title: string;
    status?: string;
    source_count?: number;
    created_at?: string;
}

export const notebooks = writable<Notebook[]>([]);
export const loading = writable(false);

export const fetchNotebooks = async () => {
    loading.set(true);
    try {
        const res = await fetch(`${PUBLIC_BACKEND_URL}/notebooks`);
        if (res.ok) {
            const data = await res.json();
            notebooks.set(data);
        }
    } catch (e) {
        console.error('Failed to fetch notebooks', e);
    } finally {
        loading.set(false);
    }
};
