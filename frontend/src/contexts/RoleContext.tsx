'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Role, DEFAULT_ROLE, ROLES, RoleInfo } from '@/lib/roles';

const STORAGE_KEY = 'gac-role';

interface RoleContextValue {
  role: Role;
  roleInfo: RoleInfo;
  setRole: (r: Role) => void;
  allRoles: RoleInfo[];
}

const RoleContext = createContext<RoleContextValue | null>(null);

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(DEFAULT_ROLE);

  // 从 localStorage 恢复（避免 SSR 不一致，挂在 effect 里）
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as Role | null;
      if (saved && ROLES.some((r) => r.id === saved)) {
        setRoleState(saved);
      }
    } catch {
      // 忽略 SSR / 隐私模式异常
    }
  }, []);

  function setRole(r: Role) {
    setRoleState(r);
    try {
      localStorage.setItem(STORAGE_KEY, r);
    } catch {
      // ignore
    }
    // 通知所有监听者（路由守卫 / 演示引导 / TopBar 徽标）
    window.dispatchEvent(new CustomEvent('gac-role-change', { detail: { role: r } }));
  }

  const roleInfo = ROLES.find((r) => r.id === role) || ROLES[0];

  return (
    <RoleContext.Provider value={{ role, roleInfo, setRole, allRoles: ROLES }}>
      {children}
    </RoleContext.Provider>
  );
}

export function useRole(): RoleContextValue {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error('useRole must be used within RoleProvider');
  return ctx;
}
