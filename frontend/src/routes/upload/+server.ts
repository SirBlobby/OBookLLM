import { json } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

export async function POST({ request, fetch }) {
    const formData = await request.formData();
    
    const res = await fetch(`${PUBLIC_BACKEND_URL}/upload`, {
        method: 'POST',
        body: formData 
    });
    
    const data = await res.json();
    return json(data);
}
