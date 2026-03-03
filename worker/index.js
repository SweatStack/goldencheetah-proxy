const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': '*',
};

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const target = url.searchParams.get('target');

    if (!target) {
      return new Response('Missing "target" query parameter', {
        status: 400,
        headers: CORS_HEADERS,
      });
    }

    let targetUrl;
    try {
      targetUrl = new URL(target);
    } catch {
      return new Response('Invalid "target" URL', {
        status: 400,
        headers: CORS_HEADERS,
      });
    }

    // Forward the path and remaining query params to the target
    const forwardUrl = new URL(url.pathname, targetUrl);
    url.searchParams.delete('target');
    forwardUrl.search = url.searchParams.toString();

    try {
      const resp = await fetch(forwardUrl.toString());
      const response = new Response(resp.body, {
        status: resp.status,
        statusText: resp.statusText,
        headers: resp.headers,
      });

      // Add CORS headers to the response
      for (const [key, value] of Object.entries(CORS_HEADERS)) {
        response.headers.set(key, value);
      }

      return response;
    } catch (err) {
      return new Response(`Proxy error: ${err.message}`, {
        status: 502,
        headers: CORS_HEADERS,
      });
    }
  },
};
