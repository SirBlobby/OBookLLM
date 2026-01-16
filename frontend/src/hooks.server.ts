import type { Handle } from '@sveltejs/kit';
import { getSession } from '$lib/server/auth';

export const handle: Handle = async ({ event, resolve }) => {
    const sessionId = event.cookies.get('session');
    
    if (sessionId) {
        const session = await getSession(sessionId);
        event.locals.session = session;
    } else {
        event.locals.session = null;
    }
    
    return resolve(event);
};