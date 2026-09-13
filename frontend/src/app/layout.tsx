import type { Metadata } from 'next';
import './globals.css';
import DemoTour from '@/components/DemoTour';
import { RoleProvider } from '@/contexts/RoleContext';
import { RoleAwareNotificationLayer } from '@/components/RoleAwareNotificationLayer';

export const metadata: Metadata = {
  title: '广汽云 ChatBI - 智能经营问数 Agent',
  description: '广汽集团智能经营分析平台，AI 驱动的自然语言问数与可视化分析',
  icons: {
    icon:
      "data:image/svg+xml," + encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 32'><defs><linearGradient id='c' x1='0' y1='0' x2='1' y2='1'><stop offset='0%25' stop-color='%23003C8F'/><stop offset='100%25' stop-color='%230050B8'/></linearGradient></defs><ellipse cx='20' cy='16' rx='19' ry='13' fill='url(%23c)'/><ellipse cx='20' cy='16' rx='19' ry='13' fill='none' stroke='%23C8102E' stroke-width='1.5'/><text x='20' y='22' text-anchor='middle' font-size='16' font-weight='900' fill='white' font-family='sans-serif'>G</text></svg>`),
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
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
        {/* 提前注入脚本，避免主题闪烁（FOUC）。默认浅色。 */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('gac-theme');if(t==='dark'){document.documentElement.classList.add('dark');}}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-screen bg-gac-gray-50">
        {/* 角色上下文（4 角色权限控制） */}
        <RoleProvider>
          {/* 通知上下文（依赖 role 过滤） */}
          <RoleAwareNotificationLayer>{children}</RoleAwareNotificationLayer>
        </RoleProvider>
        {/* P2-6: 演示模式新手引导（首次访问自动触发） */}
        <DemoTour />
      </body>
    </html>
  );
}
