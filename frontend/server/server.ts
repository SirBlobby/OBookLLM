import 'dotenv/config';
import http from 'http';

// Environment must be loaded before importing the handler
process.env.AUTH_URL = process.env.AUTH_URL || `http://localhost:${process.env.PORT || 3000}`;

// Now import the handler after env is set
const { handler } = await import('../build/handler.js');

const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';

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

// Request counter
let requestId = 0;

const server = http.createServer((req, res) => {
    const id = ++requestId;
    const start = Date.now();
    const method = req.method || 'GET';
    const url = req.url || '/';

    // Log incoming request
    console.log(
        `${colors.dim}[${timestamp()}]${colors.reset} ` +
        `${colors.bright}${colors.blue}→${colors.reset} ` +
        `${colors.magenta}#${id}${colors.reset} ` +
        `${colors.bright}${method}${colors.reset} ${url}`
    );

    // Capture original end to log response
    const originalEnd = res.end.bind(res);
    res.end = function(chunk?: any, encoding?: any, callback?: any) {
        const duration = Date.now() - start;
        const statusColor = getStatusColor(res.statusCode);
        
        console.log(
            `${colors.dim}[${timestamp()}]${colors.reset} ` +
            `${colors.bright}${colors.green}←${colors.reset} ` +
            `${colors.magenta}#${id}${colors.reset} ` +
            `${statusColor}${res.statusCode}${colors.reset} ` +
            `${colors.bright}${method}${colors.reset} ${url} ` +
            `${colors.dim}${duration}ms${colors.reset}`
        );
        
        return originalEnd(chunk, encoding, callback);
    };

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
    console.log(`  ${colors.bright}BACKEND_URL:${colors.reset} ${process.env.BACKEND_URL || process.env.PUBLIC_BACKEND_URL || 'NOT SET'}`);
    console.log(`\n${colors.dim}Ready to accept connections...${colors.reset}\n`);
});