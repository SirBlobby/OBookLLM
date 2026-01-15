import { BACKEND_URL } from '$env/static/private';

export async function POST({ request, fetch }) {
    const body = await request.json();
    
    const res = await fetch(`${BACKEND_URL}/chat`, {
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
