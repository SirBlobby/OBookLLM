import 'dotenv/config';
import http from 'http';
import https from 'https';
import { URL } from 'url';

// Environment must be loaded before importing the handler
process.env.AUTH_URL = process.env.AUTH_URL || `http://localhost:${process.env.PORT || 3000}`;

// Now import the handler after env is set
const { handler } = await import('../build/handler.js');

const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

// Color codes for terminal output
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    dim: '\x1b[2m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    red: '\x1b[31m',
};

// Status code color mapping
function getStatusColor(status: number): string {
    if (status >= 500) return colors.red;
    if (status >= 400) return colors.yellow;
    if (status >= 300) return colors.cyan;
    if (status >= 200) return colors.green;
    return colors.reset;
}

// Format timestamp
function timestamp(): string {
    return new Date().toISOString();
}

// Check if URL is a static asset (should not be logged verbosely)
function isStaticAsset(url: string): boolean {
    return url.startsWith('/_app/') || 
           url.startsWith('/favicon') ||
           url.endsWith('.js') ||
           url.endsWith('.css') ||
           url.endsWith('.png') ||
           url.endsWith('.jpg') ||
           url.endsWith('.svg') ||
           url.endsWith('.woff') ||
           url.endsWith('.woff2') ||
           url.includes('__data.json');
}

// Request counter
let requestId = 0;

// Proxy request to backend
function proxyToBackend(req: http.IncomingMessage, res: http.ServerResponse, id: number, targetPath: string) {
    const backendUrl = new URL(targetPath, BACKEND_URL);
    const protocol = backendUrl.protocol === 'https:' ? https : http;
    
    console.log(
        `${colors.dim}[${timestamp()}]${colors.reset} ` +
        `${colors.bright}${colors.yellow}⇄${colors.reset} ` +
        `${colors.magenta}#${id}${colors.reset} ` +
        `${colors.dim}PROXY${colors.reset} ${req.method} ${targetPath} → ${backendUrl.href}`
    );

    const proxyReq = protocol.request(backendUrl, {
        method: req.method,
        headers: {
            ...req.headers,
            host: backendUrl.host,
        },
    }, (proxyRes) => {
        res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
        proxyRes.pipe(res);
    });

    proxyReq.on('error', (err) => {
        console.error(
            `${colors.dim}[${timestamp()}]${colors.reset} ` +
            `${colors.red}✕ PROXY ERROR${colors.reset} ` +
            `${colors.magenta}#${id}${colors.reset}: ${err.message}`
        );
        res.statusCode = 502;
        res.end(JSON.stringify({ error: 'Backend unavailable', message: err.message }));
    });

    req.pipe(proxyReq);
}

const server = http.createServer((req, res) => {
    const id = ++requestId;
    const start = Date.now();
    const method = req.method || 'GET';
    const url = req.url || '/';
    const isStatic = isStaticAsset(url);

    // CORS headers
    const origin = req.headers.origin || '*';
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
    res.setHeader('Access-Control-Allow-Credentials', 'true');

    // Handle preflight requests
    if (method === 'OPTIONS') {
        res.statusCode = 204;
        res.end();
        return;
    }

    // Only log non-static requests on incoming
    if (!isStatic) {
        console.log(
            `${colors.dim}[${timestamp()}]${colors.reset} ` +
            `${colors.bright}${colors.blue}→${colors.reset} ` +
            `${colors.magenta}#${id}${colors.reset} ` +
            `${colors.bright}${method}${colors.reset} ${url}`
        );
    }

    // Capture original end to log response
    const originalEnd = res.end.bind(res);
    res.end = function(chunk?: any, encoding?: any, callback?: any) {
        const duration = Date.now() - start;
        const statusColor = getStatusColor(res.statusCode);
        
        // Only log non-static or error responses
        if (!isStatic || res.statusCode >= 400) {
            console.log(
                `${colors.dim}[${timestamp()}]${colors.reset} ` +
                `${colors.bright}${colors.green}←${colors.reset} ` +
                `${colors.magenta}#${id}${colors.reset} ` +
                `${statusColor}${res.statusCode}${colors.reset} ` +
                `${colors.bright}${method}${colors.reset} ${url} ` +
                `${colors.dim}${duration}ms${colors.reset}`
            );
        }
        
        return originalEnd(chunk, encoding, callback);
    };

    // Proxy /api/* requests to backend (except /api/auth/* which is handled by frontend)
    if (url.startsWith('/api/') && !url.startsWith('/api/auth/')) {
        const backendPath = url.replace('/api', '');
        proxyToBackend(req, res, id, backendPath);
        return;
    }

    handler(req, res, () => {
        console.log(
            `${colors.dim}[${timestamp()}]${colors.reset} ` +
            `${colors.red}✕${colors.reset} ` +
            `${colors.magenta}#${id}${colors.reset} ` +
            `${colors.red}404 Not Found${colors.reset}: ${url}`
        );
        res.statusCode = 404;
        res.end('Not found');
    });
});

// Graceful shutdown
const shutdown = () => {
    console.log(`\n${colors.yellow}Server shutting down...${colors.reset}`);
    server.close(() => {
        console.log(`${colors.green}Server closed${colors.reset}`);
        process.exit(0);
    });
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

server.listen(Number(PORT), HOST, () => {
    console.log(`\n${colors.bright}${colors.cyan}╔═══════════════════════════════════════════════════╗${colors.reset}`);
    console.log(`${colors.bright}${colors.cyan}║${colors.reset}         ${colors.bright}OBookLLM Frontend Server${colors.reset}              ${colors.bright}${colors.cyan}║${colors.reset}`);
    console.log(`${colors.bright}${colors.cyan}╚═══════════════════════════════════════════════════╝${colors.reset}\n`);
    console.log(`  ${colors.bright}URL:${colors.reset}         http://${HOST}:${PORT}`);
    console.log(`  ${colors.bright}AUTH_URL:${colors.reset}    ${process.env.AUTH_URL}`);
    console.log(`  ${colors.bright}AUTH_SECRET:${colors.reset} ${process.env.AUTH_SECRET ? colors.green + 'SET' + colors.reset : colors.red + 'NOT SET' + colors.reset}`);
    console.log(`  ${colors.bright}MONGODB_URI:${colors.reset} ${process.env.MONGODB_URI ? colors.green + 'SET' + colors.reset : colors.red + 'NOT SET' + colors.reset}`);
    console.log(`  ${colors.bright}BACKEND_URL:${colors.reset} ${BACKEND_URL} ${colors.dim}(internal proxy)${colors.reset}`);
    console.log(`  ${colors.bright}API Proxy:${colors.reset}   /api/* → ${BACKEND_URL}/*`);
    console.log(`\n${colors.dim}Ready to accept connections...${colors.reset}\n`);
});