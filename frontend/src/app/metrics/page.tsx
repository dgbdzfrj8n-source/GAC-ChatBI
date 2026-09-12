'use client';

import { useState } from 'react';
import GacLogo from '@/components/GacLogo';

interface Metric {
  id: string;
  code: string;
  name: string;
  domain: string;
  formula: string;
  definition: string;
  unit: string;
  icon: string;
  color: string;
}

const METRICS: Metric[] = [
  {
    id: 'M01',
    code: 'M01-SALES-FULFILLMENT',
    name: '销售达成率',
    domain: '整车销售',
    formula: 'actual_units ÷ target_units × 100%',
    definition: '实际交付量占预算目标的百分比，衡量预算执行进度的核心指标',
    unit: '%',
    icon: '📊',
    color: 'from-blue-500 to-indigo-600',
  },
  {
    id: 'M02',
    code: 'M02-UNITS-DELIVERED',
    name: '总交付量',
    domain: '整车销售',
    formula: 'COUNT(DISTINCT vin) WHERE delivery_date IS NOT NULL',
    definition: '已交付到终端用户的车辆总数，按交付日期统计',
    unit: '辆',
    icon: '🚗',
    color: 'from-emerald-500 to-teal-600',
  },
  {
    id: 'M03',
    code: 'M03-AVG-DEAL-PRICE',
    name: '单车成交均价',
    domain: '整车销售',
    formula: 'SUM(成交价 × 数量) ÷ SUM(数量)',
    definition: '含终端折扣后的实际成交均价，反映真实市场价位',
    unit: '元/辆',
    icon: '💰',
    color: 'from-amber-500 to-orange-600',
  },
  {
    id: 'M04',
    code: 'M04-MARKETING-COST',
    name: '单车营销费用',
    domain: '经营财务',
    formula: 'SUM(渠道投放金额) ÷ 总交付量',
    definition: '营销投入产出比的核心指标，越低说明效率越高',
    unit: '元/辆',
    icon: '📢',
    color: 'from-purple-500 to-pink-600',
  },
  {
    id: 'M05',
    code: 'M05-CPL',
    name: '单渠道获客成本',
    domain: '市场营销',
    formula: '渠道投放金额 ÷ 有效线索数',
    definition: 'Cost Per Lead，每获取一条有效销售线索的平均成本',
    unit: '元/条',
    icon: '🎯',
    color: 'from-rose-500 to-red-600',
  },
  {
    id: 'M06',
    code: 'M06-CONVERSION-RATE',
    name: '客流成交转化率',
    domain: '渠道经营',
    formula: '成交客户数 ÷ 进店客流量 × 100%',
    definition: '经销商门店客流转化为实际成交的比率',
    unit: '%',
    icon: '🏆',
    color: 'from-cyan-500 to-blue-600',
  },
];

const DOMAINS = ['全部', '整车销售', '经营财务', '市场营销', '渠道经营'];

export default function MetricsPage() {
  const [activeDomain, setActiveDomain] = useState('全部');

  const filtered = activeDomain === '全部'
    ? METRICS
    : METRICS.filter((m) => m.domain === activeDomain);

  return (
    <div>
      {/* 顶部说明 */}
      <div className="content-card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0"><GacLogo size="lg" /></div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gac-gray-900 mb-1">指标库</h2>
            <p className="text-sm text-gac-gray-500 leading-relaxed">
              集团统一口径的 <span className="font-semibold text-gac-primary">{METRICS.length} 个</span> 核心经营指标，
              所有 SQL 生成与报表均严格遵循以下定义，避免部门间口径不一致。
            </p>
          </div>
          <div className="text-right text-xs text-gac-gray-500">
            <div>口径版本</div>
            <div className="text-gac-primary font-semibold">v2.3.0</div>
          </div>
        </div>
      </div>

      {/* 域分类 Tab 切换 */}
      <div className="flex items-center gap-2 mb-4">
        {DOMAINS.map((d) => (
          <button
            key={d}
            onClick={() => setActiveDomain(d)}
            className={
              activeDomain === d
                ? 'px-3 py-1 bg-gac-primary text-white rounded-full text-xs font-medium'
                : 'px-3 py-1 bg-white text-gac-gray-700 border border-gac-gray-200 rounded-full text-xs font-medium hover:bg-gac-gray-100'
            }
          >
            {d}
          </button>
        ))}
      </div>

      {/* 指标卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((m) => (
          <div key={m.id} className="content-card p-5 hover:shadow-md transition-shadow">
            {/* 顶部：图标 + 编号 */}
            <div className="flex items-start justify-between mb-4">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${m.color} flex items-center justify-center text-2xl shadow-sm`}>
                {m.icon}
              </div>
              <span className="text-xs font-mono text-gac-gray-500">{m.code}</span>
            </div>

            {/* 指标名 */}
            <h3 className="text-lg font-bold text-gac-gray-900 mb-1">{m.name}</h3>
            <p className="text-xs text-gac-gray-500 mb-3">
              {m.domain} · <span className="text-gac-primary font-medium">{m.unit}</span>
            </p>

            {/* 定义 */}
            <p className="text-sm text-gac-gray-700 leading-relaxed mb-3 min-h-[60px]">
              {m.definition}
            </p>

            {/* 公式 */}
            <div className="bg-gac-gray-50 rounded-lg p-3 border border-gac-gray-200">
              <div className="text-[11px] text-gac-gray-500 mb-1 font-medium">📐 计算公式</div>
              <code className="text-xs text-gac-primary font-mono break-all">
                {m.formula}
              </code>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
