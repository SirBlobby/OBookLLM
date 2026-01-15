import { json } from '@sveltejs/kit';
import { BACKEND_URL } from '$env/static/private';

export async function GET({ fetch }) {
    const res = await fetch(`${BACKEND_URL}/notebooks`);
    const data = await res.json();
    return json(data);
}
