/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export — the FastAPI server serves the generated `out/` directory.
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
