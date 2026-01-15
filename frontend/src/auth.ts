import { SvelteKitAuth } from "@auth/sveltekit";
import Credentials from "@auth/sveltekit/providers/credentials";
import { MongoDBAdapter } from "@auth/mongodb-adapter";
import client from "$lib/db";
import { AUTH_SECRET } from "$env/static/private";

async function hashPassword(password: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export const { handle, signIn, signOut } = SvelteKitAuth({
  adapter: MongoDBAdapter(client),
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/login",
  },
  providers: [
    Credentials({
      name: "Password",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          const db = client.db("notebook_llm");
          const user = await db.collection("users").findOne({ 
            email: credentials.email 
          });

          if (!user) {
            // Fallback to demo user
            if (credentials.email === "demo@example.com" && credentials.password === "password") {
              return { id: "demo-1", name: "Demo User", email: "demo@example.com" };
            }
            return null;
          }

          // Hash password and compare
          const passwordHash = await hashPassword(credentials.password as string);

          if (user.password === passwordHash) {
            return {
              id: user._id.toString(),
              name: user.name,
              email: user.email
            };
          }

          return null;
        } catch (error) {
          console.error("Auth error:", error);
          return null;
        }
      }
    })
  ],
  secret: AUTH_SECRET,
  trustHost: true
});