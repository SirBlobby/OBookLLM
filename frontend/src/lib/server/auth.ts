import { MongoClient, ObjectId } from 'mongodb';
import { env } from '$env/dynamic/private';
import bcrypt from 'bcryptjs';

const client = new MongoClient(env.MONGODB_URI || 'mongodb://localhost:27017');

const SALT_ROUNDS = 12;

export async function hashPassword(password: string): Promise<string> {
    return bcrypt.hash(password, SALT_ROUNDS);
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
    return bcrypt.compare(password, hash);
}

export async function createSession(userId: string): Promise<string> {
    const sessionId = crypto.randomUUID();
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days
    
    const db = client.db('notebook_llm');
    await db.collection('sessions').insertOne({
        sessionId,
        userId,
        expiresAt,
        createdAt: new Date()
    });
    
    return sessionId;
}

export async function getSession(sessionId: string): Promise<{ user: { id: string; name: string; email: string } } | null> {
    if (!sessionId) return null;
    
    try {
        const db = client.db('notebook_llm');
        const session = await db.collection('sessions').findOne({
            sessionId,
            expiresAt: { $gt: new Date() }
        });
        
        if (!session) return null;
        
        const user = await db.collection('users').findOne({
            _id: new ObjectId(session.userId)
        });
        
        if (!user) return null;
        
        return {
            user: {
                id: user._id.toString(),
                name: user.name,
                email: user.email
            }
        };
    } catch (error) {
        console.error('Session error:', error);
        return null;
    }
}

export async function deleteSession(sessionId: string): Promise<void> {
    if (!sessionId) return;
    
    try {
        const db = client.db('notebook_llm');
        await db.collection('sessions').deleteOne({ sessionId });
    } catch (error) {
        console.error('Delete session error:', error);
    }
}

export async function validateCredentials(email: string, password: string): Promise<{ id: string; name: string; email: string } | null> {
    try {
        const db = client.db('notebook_llm');
        const user = await db.collection('users').findOne({ email });
        
        if (!user) {
            // Demo user fallback
            if (email === 'demo@example.com' && password === 'password') {
                return { id: 'demo-1', name: 'Demo User', email: 'demo@example.com' };
            }
            return null;
        }
        
        // Use bcrypt.compare for secure password verification
        const isValid = await verifyPassword(password, user.password);
        
        if (isValid) {
            return {
                id: user._id.toString(),
                name: user.name,
                email: user.email
            };
        }
        
        return null;
    } catch (error) {
        console.error('Validate credentials error:', error);
        return null;
    }
}

export { client };
