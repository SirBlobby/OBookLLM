import http, { type IncomingMessage, type ServerResponse } from 'node:http';
import { handler } from '../build/handler.js';
import { env } from 'node:process';

const port = env.PORT || 3000;
const host = env.HOST || '0.0.0.0';

const server = http.createServer((req: IncomingMessage, res: ServerResponse) => {
	// Add custom middleware or logic here if needed
	const start = Date.now();
	console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
	
	handler(req, res, () => {
		// next function for 404s not handled by SvelteKit (though it usually handles them)
		console.log(`[${new Date().toISOString()}] 404 Not Found: ${req.url}`);
		res.statusCode = 404;
		res.end('Not found');
	});

	res.on('finish', () => {
		const duration = Date.now() - start;
		console.log(`[${new Date().toISOString()}] ${req.method} ${req.url} ${res.statusCode} - ${duration}ms`);
	});
});

server.listen(Number(port), host, () => {
	console.log(`Listening on ${host}:${port}`);
});

// Graceful shutdown
const shutdown = () => {
	console.log('Server shutting down...');
	server.close(() => {
		console.log('Server closed');
		process.exit(0);
	});
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
