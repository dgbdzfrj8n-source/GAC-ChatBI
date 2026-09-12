// frontend/src/lib/menu.ts
// 广汽云 ChatBI 菜单结构（按 Sprint 7 规划）

export interface MenuItem {
  id: string;
  label: string;
  icon: string;
  path: string;
  description?: string;
}

export interface MenuGroup {
  id: string;
  label: string;
  icon: string;
  items: MenuItem[];
}

export const menuConfig: MenuGroup[] = [
  {
    id: 'analysis',
    label: '智能经营分析',
    icon: '📊',
    items: [
      {
        id: 'chat',
        label: '智能对话',
        icon: '💬',
        path: '/',
        description: 'AI 驱动的自然语言问数',
      },
      {
        id: 'dashboard',
        label: '驾驶舱大屏',
        icon: '🚗',
        path: '/dashboard',
        description: '4 KPI + 趋势 + 排名 + 预警',
      },
      {
        id: 'reports',
        label: '报表中心',
        icon: '📈',
        path: '/reports',
        description: '预算达成 / 销量归因 / 异常波动',
      },
    ],
  },
  {
    id: 'assets',
    label: '业务资产',
    icon: '📋',
    items: [
      {
        id: 'metrics',
        label: '指标库',
        icon: '📐',
        path: '/metrics',
        description: '6 个核心经营指标口径',
      },
      {
        id: 'tables',
        label: '数据表',
        icon: '🗄️',
        path: '/tables',
        description: '3 张事实表 Schema',
      },
      {
        id: 'history',
        label: '历史会话',
        icon: '📜',
        path: '/history',
        description: '查看历史问答记录',
      },
      {
        id: 'semantic',
        label: '语义层',
        icon: '🧠',
        path: '/semantic',
        description: '管理 NL2SQL 指标 / 维度 / 同义词',
      },
    ],
  },
  {
    id: 'system',
    label: '系统',
    icon: '⚙️',
    items: [
      {
        id: 'settings',
        label: '设置',
        icon: '⚙️',
        path: '/settings',
        description: '模型 / API / 主题',
      },
      {
        id: 'help',
        label: '帮助文档',
        icon: '📖',
        path: '/help',
        description: '使用文档 + FAQ',
      },
    ],
  },
];

// 用于快速查找页面标题（TopBar 使用）
export const pageTitleMap: Record<string, { title: string; subtitle: string; letter: string }> = {
  '/': {
    title: '智能对话',
    subtitle: '基于集团真实经营数据，AI 驱动的智能问数',
    letter: 'Z', // 智
  },
  '/dashboard': {
    title: '驾驶舱大屏',
    subtitle: '整车销售 / 经营财务 / 市场营销 / 渠道经营 一屏掌控',
    letter: 'J', // 驾
  },
  '/reports': {
    title: '报表中心',
    subtitle: '高频场景封装的标准报表模板',
    letter: 'B', // 报
  },
  '/metrics': {
    title: '指标库',
    subtitle: '6 个核心经营指标口径与定义',
    letter: 'Z', // 指
  },
  '/tables': {
    title: '数据表',
    subtitle: '3 张事实表 Schema 与示例查询',
    letter: 'S', // 数
  },
  '/history': {
    title: '历史会话',
    subtitle: '查看历史问答与查询记录',
    letter: 'L', // 历
  },
  '/semantic': {
    title: '语义层',
    subtitle: '管理 NL2SQL 指标口径 / 维度字段 / 业务同义词',
    letter: 'Y', // 语
  },
  '/settings': {
    title: '设置',
    subtitle: '模型配置 / 主题 / 接口地址',
    letter: 'S', // 设
  },
  '/help': {
    title: '帮助文档',
    subtitle: '使用文档与常见问题',
    letter: 'B', // 帮
  },
};

// 用户头像（TopBar 右上角）
export const userBadge = {
  title: 'AI 分析师',
  letter: 'A', // AI 操作员
};
