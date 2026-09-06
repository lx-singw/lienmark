/**
 * Next.js App Router Dynamic Runtime API Proxy Handler
 * Dynamically proxies client API requests to the FastAPI backend service at runtime.
 * Reads backend URL from environment on every request, streams request/response bodies,
 * forwards headers and auth tokens, and handles network errors with a defensive 502 Bad Gateway.
 * Authored strictly under Google AntiGravity for Agentic Cinema compliance.
 */

import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

interface RouteContext {
  params: Promise<{ path: string[] }>;
}

/**
 * Hop-by-hop headers that must not be blindly forwarded by reverse proxies
 */
const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'host',
]);

async function handleProxy(
  request: Request,
  context: RouteContext
): Promise<Response> {
  const { path: pathSegments = [] } = await context.params;
  const rawSegments = [...pathSegments];

  // Strip leading 'backend' if present to support both /api/backend/:path and /api/:path
  if (rawSegments.length > 0 && rawSegments[0] === 'backend') {
    rawSegments.shift();
  }

  const targetPath = rawSegments.join('/');

  const backendUrl = (
    process.env.INTERNAL_API_URL ||
    process.env.BACKEND_URL ||
    process.env.INTERNAL_BACKEND_URL ||
    process.env.BACKEND_INTERNAL_URL ||
    'http://127.0.0.1:8000'
  ).replace(/\/+$/, '');

  const incomingUrl = new URL(request.url);
  const targetUrl = targetPath
    ? `${backendUrl}/api/${targetPath}${incomingUrl.search}`
    : `${backendUrl}/api${incomingUrl.search}`;

  // Forward request headers (including Content-Type, Authorization, X-Counsel-Token, X-Session-ID, Cookie)
  const forwardHeaders = new Headers();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (!HOP_BY_HOP_HEADERS.has(lower)) {
      forwardHeaders.set(key, value);
    }
  });

  const method = request.method.toUpperCase();
  const isBodyAllowed = method !== 'GET' && method !== 'HEAD';
  const contentLength = request.headers.get('content-length');
  const hasBody = isBodyAllowed && contentLength !== '0' && request.body !== null;

  const fetchOptions: RequestInit & { duplex?: 'half' } = {
    method,
    headers: forwardHeaders,
    redirect: 'manual',
  };

  if (hasBody && request.body) {
    fetchOptions.body = request.body;
    fetchOptions.duplex = 'half';
  }

  try {
    const response = await fetch(targetUrl, fetchOptions as RequestInit);

    // Build response headers, excluding hop-by-hop and encoding headers for clean body streaming
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      const lower = key.toLowerCase();
      if (
        !HOP_BY_HOP_HEADERS.has(lower) &&
        lower !== 'content-encoding' &&
        lower !== 'content-length'
      ) {
        responseHeaders.set(key, value);
      }
    });

    // Preserve multi-cookie Set-Cookie headers when available
    if (typeof response.headers.getSetCookie === 'function') {
      const cookies = response.headers.getSetCookie();
      if (cookies && cookies.length > 0) {
        responseHeaders.delete('set-cookie');
        cookies.forEach((cookie) => {
          responseHeaders.append('set-cookie', cookie);
        });
      }
    }

    const isNoContent =
      response.status === 204 ||
      response.status === 205 ||
      response.status === 304 ||
      method === 'HEAD';

    return new Response(isNoContent ? null : response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[API Proxy 502] Failed to proxy ${method} to ${targetUrl}:`, errorMessage);

    return NextResponse.json(
      {
        error: 'Bad Gateway',
        message: `Failed to communicate with backend service at ${targetUrl}`,
        details: errorMessage,
        timestamp: new Date().toISOString(),
      },
      {
        status: 502,
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-store, max-age=0',
        },
      }
    );
  }
}

export async function GET(request: Request, context: RouteContext) {
  return handleProxy(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return handleProxy(request, context);
}

export async function PUT(request: Request, context: RouteContext) {
  return handleProxy(request, context);
}

export async function DELETE(request: Request, context: RouteContext) {
  return handleProxy(request, context);
}

export async function PATCH(request: Request, context: RouteContext) {
  return handleProxy(request, context);
}

export async function OPTIONS(request: Request, context: RouteContext) {
  return handleProxy(request, context);
}

export async function HEAD(request: Request, context: RouteContext) {
  return handleProxy(request, context);
}
