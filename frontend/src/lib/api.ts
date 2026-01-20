/**
 * API Base URL Configuration
 * 
 * In production (Docker), requests go through the frontend proxy: /api/*
 * In development, requests go directly to PUBLIC_BACKEND_URL
 */

import { browser } from '$app/environment';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

// Use /api proxy in browser when PUBLIC_BACKEND_URL is not set or is localhost
// This allows the frontend to proxy requests to the backend internally
function getApiBaseUrl(): string {
    if (!browser) {
        // Server-side: use the direct backend URL
        return PUBLIC_BACKEND_URL || 'http://localhost:8008';
    }
    
    // Client-side: check if we should use the proxy
    // If PUBLIC_BACKEND_URL is empty or set to /api, use proxy
    if (!PUBLIC_BACKEND_URL || PUBLIC_BACKEND_URL === '/api') {
        return '/api';
    }
    
    // If PUBLIC_BACKEND_URL is localhost but we're not on localhost, use proxy
    const currentHost = window.location.hostname;
    if (PUBLIC_BACKEND_URL.includes('localhost') && currentHost !== 'localhost' && currentHost !== '127.0.0.1') {
        return '/api';
    }
    
    return PUBLIC_BACKEND_URL;
}

export const API_BASE_URL = getApiBaseUrl();
