'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { pageTitleMap } from '@/lib/menu';
import { useBrand, Brand } from '@/contexts/BrandContext';
import GacBadge from './GacBadge';

const BRANDS: Brand[] = ['全部', '广汽埃安', '广汽传祺', '昊铂'];

export default function TopBar() {
  const pathname = usePathname();
  const { brand, setBrand } = useBrand();
  const [isDark, setIsDark] = useState(false);

  // 初始化与同步主题状态
  useEffect(() => {
    const root = document.documentElement;
    const saved = localStorage.getItem('gac-theme');
    if (saved === 'dark') root.classList.add('dark');
    setIsDark(root.classList.contains('dark'));
  }, []);

  const toggleTheme = () => {
    const root = document.documentElement;
    const next = !root.classList.contains('dark');
    root.classList.toggle('dark', next);
    localStorage.setItem('gac-theme', next ? 'dark' : 'light');
    setIsDark(next);
  };

  const pageInfo = pageTitleMap[pathname] ?? {
    title: '广汽云 ChatBI',
    subtitle: '智能经营分析平台',
  };

  // 品牌对应的 emoji
  const brandEmoji: Record<Brand, string> = {
    '全部': '🏢',
    '广汽埃安': '⚡',
    '广汽传祺': '🏯',
    '昊铂': '💎',
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

      {/* 右侧：主题切换 + 品牌 + 状态 + 用户 */}
      <div className="flex items-center space-x-3">
        {/* 主题切换按钮 */}
        <button
          onClick={toggleTheme}
          aria-label="切换主题"
          title={isDark ? '切换为浅色主题' : '切换为深色主题'}
          className="w-9 h-9 flex items-center justify-center rounded-lg text-gac-gray-700 hover:bg-gac-gray-100 transition-colors dark:text-gac-gray-300 dark:hover:bg-gac-gray-200"
        >
          {isDark ? (
            // 太阳图标（当前是深色 → 点击切回浅色）
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
            </svg>
          ) : (
            // 月亮图标（当前是浅色 → 点击切到深色）
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
            </svg>
          )}
        </button>

        {/* API 状态 */}
        <span className="hidden md:inline-flex text-xs px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full font-medium">
          <span className="status-dot status-online"></span>
          API 正常
        </span>

        {/* 品牌切换下拉 */}
        <div className="flex items-center gap-1.5 bg-gac-gray-100 rounded-lg px-2 py-1">
          <span className="text-sm">{brandEmoji[brand]}</span>
          <select
            value={brand}
            onChange={(e) => setBrand(e.target.value as Brand)}
            className="text-sm bg-transparent border-none focus:outline-none cursor-pointer text-gac-gray-700 font-medium"
          >
            {BRANDS.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
        </div>

        {/* 用户头像（用广汽 Logo 小号） */}
        <div className="flex items-center">
          <GacBadge size="sm" />
          <div className="ml-2 leading-tight hidden lg:block">
            <div className="text-sm font-medium text-gac-gray-900">AI 分析师</div>
            <div className="text-[11px] text-gac-gray-500">在线</div>
          </div>
        </div>
      </div>
    </header>
  );
}
