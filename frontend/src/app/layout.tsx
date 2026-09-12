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
      "data:image/svg+xml," + encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 32'><defs><linearGradient id='b' x1='0' y1='0' x2='1' y2='1'><stop offset='0%25' stop-color='%23D4152E'/><stop offset='100%25' stop-color='%23A8081F'/></linearGradient><linearGradient id='c' x1='0' y1='0' x2='1' y2='1'><stop offset='0%25' stop-color='%23003C8F'/><stop offset='100%25' stop-color='%230050B8'/></linearGradient></defs><ellipse cx='20' cy='16' rx='19' ry='12' fill='url(%23b)'/><ellipse cx='20' cy='16' rx='15.5' ry='9.5' fill='url(%23c)'/><text x='20' y='20' text-anchor='middle' font-size='11' font-weight='900' fill='white' font-family='sans-serif'>G</text></svg>`),
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
            <div className="flex-1 flex flex-col overflow-hidden pl-3">
              {/* 顶部栏 */}
              <TopBar />

              {/* 内容区（可滚动；聊天页面会用 chat-full 容器覆盖此处的内边距） */}
              <main className="flex-1 overflow-y-auto bg-gac-gray-50">
                {children}
              </main>
            </div>
          </div>
        </BrandProvider>
      </body>
    </html>
  );
}
