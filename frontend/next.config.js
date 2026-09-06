/** @type {import('next').NextConfig} */
// Runtime routing to backend is dynamically handled via app/api/[...path]/route.ts
// evaluating INTERNAL_API_URL and BACKEND_INTERNAL_URL per request to prevent build-time bake-in.
const nextConfig = {
  ...(process.env.BUILD_STANDALONE === 'true' ? { output: 'standalone' } : {}),
  reactStrictMode: true,
};

module.exports = nextConfig;
