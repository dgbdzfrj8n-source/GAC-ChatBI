// ========================================================
// P2-3: 角色权限配置（4 角色 × 10 页面矩阵）
// ========================================================
// 设计原则：
//   1. 菜单可见性 + 路由守卫 在前端处理（用户体验层）
//   2. 后端只记录角色身份，不做强制校验（演示项目无需鉴权）
//   3. 角色切换即生效（顶部下拉，一键切换身份）
// ========================================================

export type Role = 'executive' | 'analyst' | 'product' | 'guest';

export interface RoleInfo {
  id: Role;
  label: string;       // 中文名
  description: string; // 角色定位
  icon: string;        // emoji
  color: string;       // 主题色
  badge: string;       // 徽标文字（1-2 字）
}

export const ROLES: RoleInfo[] = [
  {
    id: 'executive',
    label: '高管视角',
    description: '驾驶舱大屏 / 归因报告 / 业务概览',
    icon: '👔',
    color: 'indigo',
    badge: '管',
  },
  {
    id: 'analyst',
    label: '分析师',
    description: '全量问数 + 指标库 + 数据管理 + 语义层',
    icon: '📊',
    color: 'blue',
    badge: '分',
  },
  {
    id: 'product',
    label: 'AI 产品经理',
    description: '全功能 + 语义层编辑 + 演示模式',
    icon: '🤖',
    color: 'purple',
    badge: 'PM',
  },
  {
    id: 'guest',
    label: '访客',
    description: '核心问数 + 驾驶舱大屏（只读）',
    icon: '👤',
    color: 'gray',
    badge: '客',
  },
];

export const DEFAULT_ROLE: Role = 'product';

/**
 * 权限矩阵：哪些角色能访问哪些页面
 * key = 页面路径（与路由一致）
 * value = 允许访问的角色列表
 */
export const ROLE_PERMISSIONS: Record<string, Role[]> = {
  '/':               ['executive', 'analyst', 'product', 'guest'],
  '/dashboard':      ['executive', 'analyst', 'product', 'guest'],
  '/reports':        ['executive', 'analyst', 'product'],
  '/metrics':        ['executive', 'analyst', 'product'],
  '/tables':         ['analyst', 'product'],
  '/data-manager':   ['analyst', 'product'],
  '/history':        ['analyst', 'product'],
  '/semantic':       ['product'],
  '/settings':       ['executive', 'analyst', 'product'],
  '/help':           ['executive', 'analyst', 'product', 'guest'],
};

/**
 * 是否允许某角色访问某页面
 */
export function canAccess(path: string, role: Role): boolean {
  const allowed = ROLE_PERMISSIONS[path];
  if (!allowed) return true; // 未配置的页面默认放行（避免误拦截）
  return allowed.includes(role);
}

/**
 * 获取某角色可见的菜单路径
 */
export function filterMenusByRole<T extends { path: string }>(menus: T[], role: Role): T[] {
  return menus.filter((m) => canAccess(m.path, role));
}

/**
 * 按角色获取徽标配色
 */
export function getRoleColorClasses(role: Role): {
  bg: string;
  text: string;
  ring: string;
  chip: string;
} {
  const map: Record<Role, { bg: string; text: string; ring: string; chip: string }> = {
    executive: {
      bg: 'bg-indigo-600',
      text: 'text-indigo-600',
      ring: 'ring-indigo-200',
      chip: 'bg-indigo-50 text-indigo-700',
    },
    analyst: {
      bg: 'bg-blue-600',
      text: 'text-blue-600',
      ring: 'ring-blue-200',
      chip: 'bg-blue-50 text-blue-700',
    },
    product: {
      bg: 'bg-purple-600',
      text: 'text-purple-600',
      ring: 'ring-purple-200',
      chip: 'bg-purple-50 text-purple-700',
    },
    guest: {
      bg: 'bg-gac-gray-500',
      text: 'text-gac-gray-600',
      ring: 'ring-gac-gray-200',
      chip: 'bg-gac-gray-100 text-gac-gray-700',
    },
  };
  return map[role];
}
