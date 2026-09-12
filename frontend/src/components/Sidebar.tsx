'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { menuConfig } from '@/lib/menu';
import GacLogo from './GacLogo';

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 bg-white border-r border-gac-gray-200 flex flex-col h-screen flex-shrink-0">
      {/* ====== 顶部 Logo 区 ====== */}
      <div className="h-16 flex items-center px-5 border-b border-gac-gray-200 flex-shrink-0">
        <GacLogo size={36} />
        <div className="ml-3 leading-tight">
          <div className="font-bold text-base text-gac-primary">广汽云 ChatBI</div>
          <div className="text-[11px] text-gac-gray-500 mt-0.5">智能经营分析平台</div>
        </div>
      </div>

      {/* 菜单区 */}
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

      {/* 底部版本信息 */}
      <div className="px-4 py-3 border-t border-gac-gray-200 flex-shrink-0">
        <div className="text-[11px] text-gac-gray-500 text-center leading-relaxed">
          <div>v1.8.0 · Sprint 8</div>
          <div className="text-gac-primary mt-0.5">广汽集团 · 智能经营团队</div>
        </div>
      </div>
    </aside>
  );
}
