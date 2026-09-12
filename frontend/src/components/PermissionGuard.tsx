'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useRole } from '@/contexts/RoleContext';
import { canAccess, ROLES, getRoleColorClasses, Role } from '@/lib/roles';
import Link from 'next/link';

interface ForbiddenState {
  currentRole: Role;
  pagePath: string;
}

export function PermissionGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { role } = useRole();
  const [forbidden, setForbidden] = useState<ForbiddenState | null>(null);

  useEffect(() => {
    if (!canAccess(pathname, role)) {
      setForbidden({ currentRole: role, pagePath: pathname });
    } else {
      setForbidden(null);
    }
  }, [pathname, role]);

  // 监听角色切换事件，主动跳转到第一个可见页
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as { role: Role };
      if (forbidden && detail.role !== forbidden.currentRole) {
        // 角色变了，但页面还是没权限 → 跳到首页
        if (!canAccess(pathname, detail.role)) {
          router.push('/');
        }
      }
    };
    window.addEventListener('gac-role-change', handler);
    return () => window.removeEventListener('gac-role-change', handler);
  }, [forbidden, pathname, router]);

  if (!forbidden) return <>{children}</>;
  return <ForbiddenPage state={forbidden} onSwitch={(r) => useRoleSwitch(r)} />;
}

function useRoleSwitch(_r: Role) {
  // 占位函数：实际通过 setRole 调用。这里用 window event 触发。
  const evt = new CustomEvent('gac-guard-switch', { detail: { role: _r } });
  window.dispatchEvent(evt);
}

function ForbiddenPage({ state, onSwitch }: { state: ForbiddenState; onSwitch: (r: Role) => void }) {
  const { setRole } = useRole();
  const currentRole = ROLES.find((r) => r.id === state.currentRole)!;

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-100px)] px-4">
      <div className="content-card max-w-2xl w-full p-8 text-center">
        <div className="text-6xl mb-4">🔒</div>
        <h2 className="text-xl font-semibold text-gac-gray-900 mb-2">
          当前角色无权访问此页面
        </h2>
        <p className="text-sm text-gac-gray-500 mb-6">
          页面路径：<span className="font-mono text-gac-gray-700">{state.pagePath}</span>
          <br />
          当前角色：<span className="font-medium text-gac-gray-700">{currentRole.label}</span>
          （{currentRole.description}）
        </p>

        <div className="mb-6">
          <h3 className="text-xs font-medium text-gac-gray-500 uppercase tracking-wider mb-3">
            切换到以下角色可解锁
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {ROLES.filter((r) => canAccess(state.pagePath, r.id)).map((r) => {
              const colors = getRoleColorClasses(r.id);
              return (
                <button
                  key={r.id}
                  onClick={() => setRole(r.id)}
                  className={`flex items-center gap-3 p-3 rounded-lg border ${colors.chip} hover:opacity-80 transition-opacity text-left`}
                >
                  <span className="text-2xl">{r.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium">{r.label}</div>
                    <div className="text-xs opacity-75 truncate">{r.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <Link
          href="/"
          className="inline-block px-4 py-2 text-sm text-gac-gray-700 hover:bg-gac-gray-100 rounded-lg transition-colors"
        >
          ← 返回智能对话首页
        </Link>
      </div>
    </div>
  );
}
