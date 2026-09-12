'use client';

import { useState } from 'react';
import GacBadge from '@/components/GacBadge';

interface Report {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  tags: string[];
}

const REPORTS: Report[] = [
  {
    id: 'budget-fulfillment',
    name: '预算达成分析',
    description: '各品牌、各大区、各车型的预算完成进度，自动识别达成率低于 90% 的薄弱项',
    icon: '📊',
    category: '整车销售',
    tags: ['月度', '预算', '达成率'],
  },
  {
    id: 'sales-attribution',
    name: '销量归因分析',
    description: '通过 SOP 四步归因引擎，定位销量波动的根因（渠道 / 大区 / 价格 / 产品）',
    icon: '🔍',
    category: '整车销售',
    tags: ['归因', 'SOP', '波动'],
  },
  {
    id: 'channel-roi',
    name: '渠道投放 ROI',
    description: '各营销渠道的投放金额、线索量、转化率、CPL 等关键指标横向对比',
    icon: '💰',
    category: '市场营销',
    tags: ['渠道', 'ROI', 'CPL'],
  },
  {
    id: 'inventory-warning',
    name: '库存预警报表',
    description: '经销商库存周转天数、库存系数、超期库存车辆明细，辅助补货决策',
    icon: '⚠️',
    category: '经营财务',
    tags: ['库存', '预警', '周转'],
  },
  {
    id: 'conversion-funnel',
    name: '客流转化漏斗',
    description: '从客流 → 留资 → 试驾 → 成交的全链路转化率分析，定位流失环节',
    icon: '🎯',
    category: '渠道经营',
    tags: ['漏斗', '转化率', '客流'],
  },
  {
    id: 'regional-ranking',
    name: '大区销售排行',
    description: '7 大区销售业绩排行，含同比、环比、达成率多维度对比',
    icon: '🏆',
    category: '整车销售',
    tags: ['大区', '排行', '同比'],
  },
];

const CATEGORIES = ['全部', '整车销售', '经营财务', '市场营销', '渠道经营'];

export default function ReportsPage() {
  const [activeCategory, setActiveCategory] = useState('全部');
  const filtered = activeCategory === '全部'
    ? REPORTS
    : REPORTS.filter((r) => r.category === activeCategory);

  return (
    <div className="content-wrap">
      {/* 顶部说明 */}
      <div className="content-card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0"><GacBadge size="lg" /></div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gac-gray-900 mb-1">报表中心</h2>
            <p className="text-sm text-gac-gray-500 leading-relaxed">
              高频经营场景的标准报表模板，集成 SOP 归因引擎与指标口径，可一键导出与定时订阅。
              <span className="text-gac-primary font-medium ml-2">共 {REPORTS.length} 个标准报表</span>
            </p>
          </div>
        </div>
      </div>

      {/* 分类筛选 */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={
              activeCategory === cat
                ? 'btn-primary'
                : 'px-4 py-2 bg-white text-gac-gray-700 border border-gac-gray-200 rounded-lg text-sm font-medium hover:bg-gac-gray-100'
            }
          >
            {cat}
          </button>
        ))}
      </div>

      {/* 报表卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((report) => (
          <div
            key={report.id}
            className="content-card p-5 hover:shadow-md hover:border-gac-primary transition-all cursor-pointer"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="text-3xl">{report.icon}</div>
              <span className="text-xs px-2 py-1 bg-blue-50 text-gac-primary rounded">
                {report.category}
              </span>
            </div>
            <h3 className="text-base font-semibold text-gac-gray-900 mb-2">
              {report.name}
            </h3>
            <p className="text-sm text-gac-gray-500 leading-relaxed mb-4 min-h-[48px]">
              {report.description}
            </p>
            <div className="flex items-center justify-between">
              <div className="flex flex-wrap gap-1">
                {report.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[11px] px-2 py-0.5 bg-gac-gray-100 text-gac-gray-700 rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <button className="text-xs text-gac-primary font-medium hover:underline">
                查看 →
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
