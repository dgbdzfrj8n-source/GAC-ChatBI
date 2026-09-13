// ========================================================
// P2-5: 通知类型定义
// ========================================================

export type NotificationType =
  | 'sop_complete'      // 深度归因 SOP 完成
  | 'alert_kpi'          // KPI 异常预警
  | 'budget_deviation'   // 预算偏差
  | 'new_question'       // 用户新问数
  | 'badcase_feedback'   // Bad Case 反馈
  | 'task_assign'        // AI PM 派发任务
  | 'system';            // 系统消息

export type NotificationSeverity = 'info' | 'success' | 'warning' | 'error';

export interface NotificationItem {
  id: string;
  type: NotificationType;
  severity: NotificationSeverity;
  title: string;
  body: string;
  /** ISO 时间字符串 */
  timestamp: string;
  read: boolean;
  /** 可选链接（点击跳转） */
  link?: string;
  /** 角色过滤：空 = 全部角色可见 */
  audience?: ('executive' | 'analyst' | 'product' | 'guest')[];
  /** 关联问数（可选） */
  queryId?: string;
}

export interface NotificationTypeMeta {
  label: string;
  icon: string;
  /** Tailwind 颜色类（徽标背景） */
  badgeBg: string;
  badgeText: string;
  /** 优先级（排序用） */
  priority: number;
}

export const NOTIFICATION_META: Record<NotificationType, NotificationTypeMeta> = {
  sop_complete:    { label: '深度归因', icon: '🔍', badgeBg: 'bg-purple-100', badgeText: 'text-purple-700', priority: 9 },
  alert_kpi:       { label: 'KPI 预警', icon: '🚨', badgeBg: 'bg-red-100',    badgeText: 'text-red-700',    priority: 10 },
  budget_deviation:{ label: '预算偏差', icon: '📉', badgeBg: 'bg-orange-100', badgeText: 'text-orange-700', priority: 8 },
  new_question:    { label: '问数',     icon: '💬', badgeBg: 'bg-blue-100',   badgeText: 'text-blue-700',   priority: 5 },
  badcase_feedback:{ label: 'Bad Case', icon: '👍', badgeBg: 'bg-emerald-100',badgeText: 'text-emerald-700',priority: 4 },
  task_assign:     { label: '任务',     icon: '📋', badgeBg: 'bg-indigo-100', badgeText: 'text-indigo-700', priority: 7 },
  system:          { label: '系统',     icon: '⚙️', badgeBg: 'bg-gac-gray-100',badgeText: 'text-gac-gray-700', priority: 3 },
};
