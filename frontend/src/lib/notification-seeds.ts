// ========================================================
// P2-5: 通知种子数据生成器
// 根据当前时间生成 7-12 条演示通知，覆盖 7 类场景
// ========================================================

import { NotificationItem, NotificationType } from './notifications';

const NOW = () => new Date();

function offsetMinutes(min: number): string {
  const d = NOW();
  d.setMinutes(d.getMinutes() - min);
  return d.toISOString();
}

const SAMPLES: Array<Omit<NotificationItem, 'id' | 'timestamp' | 'read'>> = [
  {
    type: 'alert_kpi',
    severity: 'error',
    title: '🚨 广汽传祺 3 月销量达成率仅 71%',
    body: '距预算缺口 1800 台，建议立即触发深度归因 SOP',
    link: '/dashboard',
    audience: ['executive', 'analyst', 'product'],
  },
  {
    type: 'sop_complete',
    severity: 'success',
    title: '🔍 深度归因完成：昊铂 3 月销量下滑',
    body: '4 步归因报告已生成，主因 = 三线城市体验店到店量环比下降 23%',
    link: '/history',
    audience: ['executive', 'analyst', 'product'],
  },
  {
    type: 'budget_deviation',
    severity: 'warning',
    title: '📉 营销渠道 CPL 超预算 12%',
    body: '广汽埃安抖音渠道 3 月 CPL 达 ¥328，超预算上限 ¥300',
    link: '/semantic',
    audience: ['analyst', 'product'],
  },
  {
    type: 'new_question',
    severity: 'info',
    title: '💬 张总提问：2025-Q1 各品牌市场份额',
    body: '高管视角，3 分钟后回应完成（耗时 1.2s）',
    link: '/history',
    audience: ['executive', 'analyst', 'product'],
  },
  {
    type: 'task_assign',
    severity: 'info',
    title: '📋 新任务：补充 2025-Q2 区域销售预测口径',
    body: '来自 AI 产品经理，截止日期 2025-04-15',
    link: '/semantic',
    audience: ['product'],
  },
  {
    type: 'badcase_feedback',
    severity: 'success',
    title: '👍 用户采纳了你的口径修正建议',
    body: '"4 月新能源销量达成率" 已自动并入指标库',
    link: '/semantic',
    audience: ['analyst', 'product'],
  },
  {
    type: 'system',
    severity: 'info',
    title: '⚙️ 系统已升级到 v1.8.0',
    body: '本次更新：新增数据管理 / 4 角色权限 / 演示模式',
    link: '/help',
  },
  {
    type: 'alert_kpi',
    severity: 'error',
    title: '🚨 昊铂 3 月毛利率跌至 18.2%',
    body: '环比下降 4.5 个百分点，低于行业警戒线 20%',
    link: '/dashboard',
    audience: ['executive', 'analyst', 'product'],
  },
  {
    type: 'new_question',
    severity: 'info',
    title: '💬 王分析师提问：广汽传祺经销商库存周转',
    body: '分析师视角，5 分钟后回应完成（耗时 2.1s）',
    link: '/history',
    audience: ['analyst', 'product'],
  },
  {
    type: 'budget_deviation',
    severity: 'warning',
    title: '📉 广汽埃安展厅客流转化率低于目标',
    body: '广州天河店转化率 8.7%，目标值 12%',
    link: '/semantic',
    audience: ['analyst', 'product'],
  },
  {
    type: 'sop_complete',
    severity: 'success',
    title: '🔍 归因报告：广汽传祺经销商网络下沉',
    body: '4 步归因：主因 = 三线城市网络密度不足，副因 = 售后服务网点不足',
    link: '/history',
    audience: ['executive', 'analyst', 'product'],
  },
  {
    type: 'system',
    severity: 'info',
    title: '⚙️ 语义层已更新',
    body: '指标层新增 "新能源渗透率"，6 个指标已审核通过',
    link: '/semantic',
    audience: ['analyst', 'product'],
  },
];

const OFFSETS = [1, 3, 8, 15, 30, 45, 75, 120, 180, 240, 360, 720]; // 分钟前

export function generateSeedNotifications(): NotificationItem[] {
  return SAMPLES.map((s, i) => ({
    ...s,
    id: `seed-${i + 1}`,
    timestamp: offsetMinutes(OFFSETS[i] ?? (i + 1) * 60),
    read: i >= 8, // 后 4 条标记为已读
  }));
}
