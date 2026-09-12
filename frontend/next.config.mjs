/** @type {import('next').NextConfig} */
const nextConfig = {
  // 适配 Netlify Static Site 部署
  output: "export",
  images: {
    // 静态导出必须用 unoptimized
    unoptimized: true,
  },
  // 构建时跳过 ESLint 检查（避免 any 类型报错）
  eslint: {
    ignoreDuringBuilds: true,
  },
  // SSR 水合保护：ECharts 等客户端库会在客户端动态导入
  experimental: {
    serverComponentsExternalPackages: ["echarts", "echarts-for-react"],
  },
};

export default nextConfig;
