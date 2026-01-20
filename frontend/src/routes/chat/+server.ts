import { error } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export async function POST({ request, fetch, locals }) {
    if (!locals.session?.user) {
        throw error(401, 'Unauthorized');
    }

    const body = await request.json();
    
    const res = await fetch(`${env.BACKEND_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });

    return new Response(res.body, {
        headers: {
            'Content-Type': 'text/plain'
        }
    });
}
