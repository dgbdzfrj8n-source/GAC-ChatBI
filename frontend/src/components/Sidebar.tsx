'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { menuConfig } from '@/lib/menu';
import { filterMenusByRole } from '@/lib/roles';
import { useRole } from '@/contexts/RoleContext';
import GacLogo from './GacLogo';

export default function Sidebar() {
  const pathname = usePathname();
  const { role, roleInfo } = useRole();

  // 按角色过滤菜单
  const filteredConfig = menuConfig
    .map((group) => ({
      ...group,
      items: filterMenusByRole(group.items, role),
    }))
    .filter((group) => group.items.length > 0);

  return (
    <aside data-tour="sidebar" className="w-60 bg-white border-r border-gac-gray-200 flex flex-col h-screen flex-shrink-0 dark:bg-gac-gray-900 dark:border-gac-gray-700">
      {/* ====== 顶部 Logo 区 ====== */}
      <div className="h-16 flex items-center px-4 border-b border-gac-gray-200 flex-shrink-0 gap-3 dark:border-gac-gray-700">
        <GacLogo size={40} />
        <div className="leading-tight min-w-0">
          <div className="font-bold text-[15px] leading-snug text-gac-gray-900 dark:text-white truncate">
            广汽云 ChatBI
          </div>
          <div className="text-[11px] mt-0.5 text-gac-gray-500 dark:text-gac-gray-400 truncate">
            智能经营分析平台
          </div>
        </div>
      </div>

      {/* ====== 当前角色徽标（P2-3） ====== */}
      <div
        data-tour="role-badge"
        className="px-4 py-2.5 border-b border-gac-gray-200 dark:border-gac-gray-700 flex items-center gap-2 bg-gac-gray-50/50 dark:bg-gac-gray-800/30"
      >
        <span className="text-base">{roleInfo.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-gac-gray-900 dark:text-white truncate">
            当前视角 · {roleInfo.label}
          </div>
          <div className="text-[10px] text-gac-gray-500 truncate">
            {roleInfo.description}
          </div>
        </div>
      </div>

      {/* 菜单区 */}
      <nav className="flex-1 overflow-y-auto py-2 scrollbar-thin">
        {filteredConfig.map((group, gi) => (
          <div key={group.id} className="mb-2" data-tour={`menu-group-${group.id}`}>
            <div className="menu-group-title">
              {group.label}
            </div>
            {group.items.map((item) => {
              const isActive = pathname === item.path;
              return (
                <Link
                  key={item.id}
                  href={item.path}
                  data-tour={`menu-item-${item.id}`}
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
        {/* 角色无权限时提示 */}
        {filteredConfig.length === 0 && (
          <div className="px-4 py-8 text-center text-xs text-gac-gray-400">
            当前角色无可见菜单
          </div>
        )}
      </nav>

      {/* 底部版本信息 */}
      <div className="px-4 py-3 border-t border-gac-gray-200 flex-shrink-0">
        <div className="text-[11px] text-gac-gray-500 text-center leading-relaxed">
          <div>v1.9.0 · Sprint 9</div>
          <div className="text-gac-primary mt-0.5 font-medium">谢志锋</div>
        </div>
      </div>
    </aside>
  );
}
