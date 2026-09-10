/** @type {import('next').NextConfig} */
const nextConfig = {
  // SSR 水合保护：ECharts 等客户端库会在客户端动态导入
  experimental: {
    serverComponentsExternalPackages: ["echarts", "echarts-for-react"],
  },
};

export default nextConfig;
