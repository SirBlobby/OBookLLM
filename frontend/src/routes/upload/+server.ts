import { json } from '@sveltejs/kit';
import { BACKEND_URL } from '$env/static/private';

export async function POST({ request, fetch }) {
    const formData = await request.formData();
    
    // We can't directly forward the Request object's FormData because of boundary issues,
    // but we can forward the body if we let the browser/fetch handle the boundary or reconstruct it.
    // However, in SvelteKit + node adapter, forwarding the body directly is often easiest.
    
    // Easier approach: just forward the incoming formData to the backend
    // But fetch doesn't like passing formData directly from request.formData() sometimes.
    // Let's rely on standard fetch behavior:
    
    const res = await fetch(`${BACKEND_URL}/upload`, {
        method: 'POST',
        body: formData 
        // Note: Do NOT set Content-Type header when passing FormData, 
        // fetch will set it with the correct boundary.
    });
    
    const data = await res.json();
    return json(data);
}
