import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';
import { BrandProvider } from '@/contexts/BrandContext';

export const metadata: Metadata = {
  title: '广汽云 ChatBI - 智能经营问数 Agent',
  description: '广汽集团智能经营分析平台，AI 驱动的自然语言问数与可视化分析',
  icons: {
    icon:
      "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='%23003C8F' stroke='%23C8102E' stroke-width='2'/><text x='16' y='22' text-anchor='middle' font-size='16' font-weight='bold' fill='white'>G</text></svg>",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-gac-gray-50">
        {/* 品牌上下文（全局状态） */}
        <BrandProvider>
          {/* ====== 主体：左侧菜单 + 右侧内容 ====== */}
          <div className="flex h-screen overflow-hidden">
            {/* 左侧侧边栏 */}
            <Sidebar />

            {/* 右侧主区域 */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* 顶部栏 */}
              <TopBar />

              {/* 内容区 */}
              <main className="content-area">
                <div className="p-6 max-w-[1600px] mx-auto">{children}</div>
              </main>
            </div>
          </div>
        </BrandProvider>
      </body>
    </html>
  );
}
