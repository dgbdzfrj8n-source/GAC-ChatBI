'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import { pageTitleMap } from '@/lib/menu';
import { useBrand, Brand } from '@/contexts/BrandContext';
import { useRole } from '@/contexts/RoleContext';
import { getRoleColorClasses } from '@/lib/roles';
import NotificationBell from '@/components/NotificationBell';
import GacBadge from './GacBadge';
import { userBadge } from '@/lib/menu';

const BRANDS: Brand[] = ['全部', '广汽埃安', '广汽传祺', '昊铂'];

export default function TopBar() {
  const pathname = usePathname();
  const { brand, setBrand } = useBrand();
  const { role, roleInfo, setRole, allRoles } = useRole();
  const [isDark, setIsDark] = useState(false);
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const roleMenuRef = useRef<HTMLDivElement>(null);

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

  // 点击外部关闭角色菜单
  useEffect(() => {
    if (!roleMenuOpen) return;
    const handler = (e: MouseEvent) => {
      if (roleMenuRef.current && !roleMenuRef.current.contains(e.target as Node)) {
        setRoleMenuOpen(false);
      }
    };
    window.addEventListener('mousedown', handler);
    return () => window.removeEventListener('mousedown', handler);
  }, [roleMenuOpen]);

  // 路由变化关闭菜单
  useEffect(() => {
    setRoleMenuOpen(false);
  }, [pathname]);

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

        {/* 角色切换器（P2-3） */}
        <div ref={roleMenuRef} className="relative">
          <button
            onClick={() => setRoleMenuOpen((v) => !v)}
            aria-label="切换角色视角"
            data-tour="role-switcher"
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors ${getRoleColorClasses(role).chip} hover:opacity-80`}
          >
            <span>{roleInfo.icon}</span>
            <span className="hidden sm:inline">{roleInfo.label}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${roleMenuOpen ? 'rotate-180' : ''}`}>
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          {roleMenuOpen && (
            <div className="absolute right-0 top-full mt-2 w-72 bg-white dark:bg-gac-gray-900 rounded-xl shadow-xl border border-gac-gray-200 dark:border-gac-gray-700 z-50 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-gac-gray-100 dark:border-gac-gray-800 text-xs text-gac-gray-500">
                切换视角 · 不同角色看到不同菜单与功能
              </div>
              {allRoles.map((r) => {
                const colors = getRoleColorClasses(r.id);
                const isActive = r.id === role;
                return (
                  <button
                    key={r.id}
                    onClick={() => {
                      setRole(r.id);
                      setRoleMenuOpen(false);
                    }}
                    className={`w-full flex items-start gap-3 px-4 py-2.5 hover:bg-gac-gray-50 dark:hover:bg-gac-gray-800 transition-colors text-left ${
                      isActive ? 'bg-gac-gray-50 dark:bg-gac-gray-800' : ''
                    }`}
                  >
                    <span className="text-xl flex-shrink-0">{r.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gac-gray-900 dark:text-white">
                          {r.label}
                        </span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${colors.chip}`}>
                          {r.badge}
                        </span>
                        {isActive && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-medium">
                            当前
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gac-gray-500 mt-0.5 leading-snug">
                        {r.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

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

        {/* 通知中心（P2-5） */}
        <NotificationBell />

        {/* 演示模式按钮（P2-6） */}
        <button
          onClick={() => window.dispatchEvent(new Event('gac-tour-start'))}
          aria-label="重新触发新手引导"
          title="新手引导 / 演示模式"
          className="w-9 h-9 flex items-center justify-center rounded-lg text-gac-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors dark:text-gac-gray-300"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </button>

        {/* 用户头像（用页面徽标） */}
        <div className="flex items-center">
          <GacBadge size="sm" letter={userBadge.letter} />
          <div className="ml-2 leading-tight hidden lg:block">
            <div className="text-sm font-medium text-gac-gray-900">{userBadge.title}</div>
            <div className="text-[11px] text-gac-gray-500">在线</div>
          </div>
        </div>
      </div>
    </header>
  );
}
