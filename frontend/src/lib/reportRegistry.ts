/**
 * 报表中心中央注册表 (Sprint 8)
 * 数据来源：后端 /api/reports/registry，但前端保留一份常量做 SSR/降级用。
 */
export interface ReportMeta {
  report_id: string;
  name: string;
  category: string;
  description: string;
  icon: string;
  status: 'ready' | 'mocked' | 'wip';
}

export const REPORT_REGISTRY: Record<string, ReportMeta> = {
  'budget-fulfillment': {
    report_id: 'budget-fulfillment',
    name: '预算达成分析',
    category: '整车销售',
    description: '本月各品牌预算完成进度，自动识别达成率低于 95% 的薄弱项。',
    icon: '🎯',
    status: 'ready',
  },
  'sales-attribution': {
    report_id: 'sales-attribution',
    name: '销量归因分析',
    category: '整车销售',
    description: '销量同比/环比波动的多维根因：渠道 / 大区 / 价格带瀑布图。',
    icon: '📈',
    status: 'ready',
  },
  'channel-roi': {
    report_id: 'channel-roi',
    name: '渠道投放 ROI',
    category: '市场营销',
    description: '各营销渠道的获客成本 (CPL)、转化率与投资回报率。',
    icon: '💰',
    status: 'ready',
  },
  'inventory-warning': {
    report_id: 'inventory-warning',
    name: '库存预警',
    category: '库存管理',
    description: '经销商库存周转天数、库存系数与高库存预警。',
    icon: '📦',
    status: 'ready',
  },
  'conversion-funnel': {
    report_id: 'conversion-funnel',
    name: '客流转化漏斗',
    category: '渠道经营',
    description: '进店→留资→试驾→成交 4 级漏斗转化分析。',
    icon: '🌪️',
    status: 'ready',
  },
  'regional-ranking': {
    report_id: 'regional-ranking',
    name: '大区销售排行',
    category: '整车销售',
    description: '5 大区业绩多维对比 + 近 12 月趋势。',
    icon: '🏆',
    status: 'ready',
  },
};

export const REPORT_IDS = Object.keys(REPORT_REGISTRY);
