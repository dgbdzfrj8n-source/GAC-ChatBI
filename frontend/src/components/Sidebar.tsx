'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { menuConfig } from '@/lib/menu';

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 bg-white border-r border-gac-gray-200 flex flex-col h-screen flex-shrink-0">
      {/* ====== 顶部 Logo 区 ====== */}
      <div className="h-16 flex items-center px-5 border-b border-gac-gray-200 flex-shrink-0">
        <div className="gac-logo mr-3">G</div>
        <div className="leading-tight">
          <div className="font-bold text-base text-gac-primary">广汽云 ChatBI</div>
          <div className="text-[11px] text-gac-gray-500 mt-0.5">智能经营分析平台</div>
        </div>
      </div>

      {/* ====== 菜单区 ====== */}
      <nav className="flex-1 overflow-y-auto py-2 scrollbar-thin">
        {menuConfig.map((group) => (
          <div key={group.id} className="mb-2">
            <div className="menu-group-title">
              {group.label}
            </div>
            {group.items.map((item) => {
              const isActive = pathname === item.path;
              return (
                <Link
                  key={item.id}
                  href={item.path}
                  className={isActive ? 'menu-item menu-item-active' : 'menu-item'}
                >
                  <span className="mr-3 text-base">{item.icon}</span>
                  <span className="flex-1">{item.label}</span>
                  {isActive && (
                    <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* ====== 底部信息 ====== */}
      <div className="p-4 border-t border-gac-gray-200 flex-shrink-0">
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-3">
          <div className="flex items-center mb-2">
            <span className="status-dot status-online"></span>
            <span className="text-xs font-medium text-gac-gray-700">系统运行正常</span>
          </div>
          <div className="text-[11px] text-gac-gray-500 leading-relaxed">
            <div>Sprint 7 已上线</div>
            <div>v1.7.0 · 2026.09</div>
            <div className="mt-1 text-gac-primary font-medium">广汽集团 · 智能经营团队</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
