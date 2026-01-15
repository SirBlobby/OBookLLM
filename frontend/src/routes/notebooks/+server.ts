import { json, error } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export async function GET({ fetch, locals }) {
    const session = await locals.auth();
    if (!session?.user) {
        throw error(401, 'Unauthorized');
    }

    const res = await fetch(`${env.BACKEND_URL}/notebooks`);
    const data = await res.json();
    return json(data);
}
