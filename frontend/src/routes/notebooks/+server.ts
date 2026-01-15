import { json } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

export async function GET({ fetch }) {
    const res = await fetch(`${PUBLIC_BACKEND_URL}/notebooks`);
    const data = await res.json();
    return json(data);
}
