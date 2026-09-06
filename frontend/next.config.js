/** @type {import('next').NextConfig} */
const nextConfig = {
  ...(process.env.BUILD_STANDALONE === 'true' ? { output: 'standalone' } : {}),
  reactStrictMode: true,
  async rewrites() {
    const backendUrl =
      process.env.INTERNAL_API_URL ||
      process.env.BACKEND_INTERNAL_URL ||
      process.env.INTERNAL_BACKEND_URL ||
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://127.0.0.1:8000';
    return [
      {
        source: '/api/backend/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
