import { json } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

export async function POST({ request, fetch }) {
    const body = await request.json();
    
    const res = await fetch(`${PUBLIC_BACKEND_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    
    const data = await res.json();
    
    // Forward the status code as well
    if (!res.ok) {
        return json(data, { status: res.status });
    }
    
    return json(data);
}
