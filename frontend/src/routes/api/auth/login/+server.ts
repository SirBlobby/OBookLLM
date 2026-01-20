import { json, redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { validateCredentials, createSession } from '$lib/server/auth';

export const POST: RequestHandler = async ({ request, cookies }) => {
    const { email, password } = await request.json();
    
    if (!email || !password) {
        return json({ error: 'Email and password are required' }, { status: 400 });
    }
    
    const user = await validateCredentials(email, password);
    
    if (!user) {
        return json({ error: 'Invalid email or password' }, { status: 401 });
    }
    
    const sessionId = await createSession(user.id);
    
    cookies.set('session', sessionId, {
        path: '/',
        httpOnly: true,
        sameSite: 'lax',
        secure: false, // Set to true in production with HTTPS
        maxAge: 60 * 60 * 24 * 7 // 7 days
    });
    
    return json({ success: true, user });
};
