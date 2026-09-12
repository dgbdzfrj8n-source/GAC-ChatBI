'use client';

import { usePathname } from 'next/navigation';
import { pageTitleMap } from '@/lib/menu';

export default function TopBar() {
  const pathname = usePathname();
  const pageInfo = pageTitleMap[pathname] ?? {
    title: '广汽云 ChatBI',
    subtitle: '智能经营分析平台',
  };

  return (
    <header className="topbar">
      {/* 左侧：页面标题 */}
      <div>
        <h1 className="text-lg font-semibold text-gac-gray-900 leading-tight">
          {pageInfo.title}
        </h1>
        <p className="text-xs text-gac-gray-500 mt-0.5">{pageInfo.subtitle}</p>
      </div>

      {/* 右侧：状态 + 用户 */}
      <div className="flex items-center space-x-4">
        <span className="hidden md:inline-flex text-xs px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full font-medium">
          <span className="status-dot status-online"></span>
          API 正常
        </span>
        <button className="hidden md:block text-xs px-3 py-1 bg-gac-gray-100 text-gac-gray-700 rounded-full hover:bg-gac-gray-200">
          🔄 切换品牌
        </button>
        <div className="flex items-center">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-gac-primary to-gac-primary-light text-white flex items-center justify-center font-semibold text-sm border-2 border-gac-accent">
            AI
          </div>
          <div className="ml-2 leading-tight hidden lg:block">
            <div className="text-sm font-medium text-gac-gray-900">AI 分析师</div>
            <div className="text-[11px] text-gac-gray-500">在线</div>
          </div>
        </div>
      </div>
    </header>
  );
}
