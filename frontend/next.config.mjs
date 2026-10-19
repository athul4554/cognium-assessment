/** @type {import('next').NextConfig} */
const nextConfig = {
  // Browser calls /api/* on the Next.js server, which forwards to FastAPI.
  // No CORS headaches, and the frontend never hardcodes the backend URL.
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
