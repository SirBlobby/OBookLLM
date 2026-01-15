import { json } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

export async function POST({ request, fetch }) {
    const body = await request.json();
    const res = await fetch(`${PUBLIC_BACKEND_URL}/notebooks/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    const data = await res.json();
    return json(data);
}
