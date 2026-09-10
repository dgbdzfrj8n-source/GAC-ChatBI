import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "广汽云 ChatBI - 智能经营问数 Agent",
  description: "广汽集团智能经营分析平台，AI 驱动的自然语言问数与可视化分析",
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='24' font-size='24'>🚗</text></svg>",
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
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-gray-50">
        {/* 顶部导航条 */}
        <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-bold text-sm">
                GAC
              </div>
              <span className="font-semibold text-gray-900 hidden sm:block">广汽云 ChatBI</span>
              <span className="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full font-medium">
                Beta
              </span>
            </div>

            <div className="flex items-center gap-3">
              {/* 品牌切换 */}
              <select className="text-sm border border-gray-200 rounded-lg px-2 py-1 text-gray-600 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
                <option>全部品牌</option>
                <option>广汽埃安</option>
                <option>广汽传祺</option>
                <option>昊铂</option>
              </select>

              {/* 模式切换 */}
              <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                <button className="px-3 py-1 text-xs rounded-md bg-white shadow-sm font-medium text-gray-900 transition-all">
                  实时模式
                </button>
                <button className="px-3 py-1 text-xs rounded-md text-gray-500 hover:text-gray-700 transition-all">
                  演示模式
                </button>
              </div>

              {/* API 状态指示 */}
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs text-gray-500">API 正常</span>
              </div>
            </div>
          </div>
        </header>

        <main>{children}</main>
      </body>
    </html>
  );
}
