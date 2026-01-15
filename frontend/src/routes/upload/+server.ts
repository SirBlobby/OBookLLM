import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export async function POST({ request, fetch }) {
    const formData = await request.formData();
    
    const res = await fetch(`${env.BACKEND_URL}/upload`, {
        method: 'POST',
        body: formData 
    });
    
    const data = await res.json();
    return json(data);
}
