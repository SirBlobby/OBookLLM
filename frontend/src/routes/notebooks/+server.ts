import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export async function GET({ fetch }) {
    const res = await fetch(`${env.BACKEND_URL}/notebooks`);
    const data = await res.json();
    return json(data);
}
