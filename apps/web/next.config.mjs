/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output keeps the production Docker image small (only the
  // traced dependency subset is copied in) - see apps/web/Dockerfile.
  output: "standalone",
};

export default nextConfig;
