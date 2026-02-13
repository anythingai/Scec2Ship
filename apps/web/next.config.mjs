/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  output: 'standalone',
  async rewrites() {
    const apiBase = process.env.API_BASE_URL || 'http://localhost:8000'
    return [
      { source: '/health', destination: `${apiBase}/health` },
      { source: '/workspaces', destination: `${apiBase}/workspaces` },
      { source: '/workspaces/:path*', destination: `${apiBase}/workspaces/:path*` },
      { source: '/runs', destination: `${apiBase}/runs` },
      { source: '/runs/:path*', destination: `${apiBase}/runs/:path*` },
      { source: '/auth/:path*', destination: `${apiBase}/auth/:path*` },
      { source: '/sample/:path*', destination: `${apiBase}/sample/:path*` },
      { source: '/integrations', destination: `${apiBase}/integrations` },
      { source: '/integrations/:path*', destination: `${apiBase}/integrations/:path*` },
      { source: '/competitor-gap', destination: `${apiBase}/competitor-gap` },
      { source: '/audit-trail', destination: `${apiBase}/audit-trail` },
      { source: '/metrics', destination: `${apiBase}/metrics` },
      { source: '/webhooks/:path*', destination: `${apiBase}/webhooks/:path*` },
    ]
  },
}

export default nextConfig
