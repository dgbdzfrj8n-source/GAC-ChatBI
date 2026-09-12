'use client';

import GacBadge from '@/components/GacBadge';

interface Column {
  name: string;
  type: string;
  description: string;
  pk?: boolean;
}

interface Table {
  name: string;
  fullName: string;
  description: string;
  icon: string;
  rows: string;
  columns: Column[];
}

const TABLES: Table[] = [
  {
    name: 'fact_sales_daily',
    fullName: '日销售事实表',
    description: '记录每一辆车的销售明细，是销量与营收分析的核心表',
    icon: '🚗',
    rows: '约 18,500 行',
    columns: [
      { name: 'sale_id', type: 'VARCHAR', description: '销售单 ID（主键）', pk: true },
      { name: 'sale_date', type: 'DATE', description: '销售日期' },
      { name: 'brand_code', type: 'VARCHAR', description: '品牌编码（埃安/传祺/昊铂）' },
      { name: 'model_code', type: 'VARCHAR', description: '车型编码' },
      { name: 'region_code', type: 'VARCHAR', description: '大区编码（华东/华南等）' },
      { name: 'dealer_id', type: 'VARCHAR', description: '经销商 ID' },
      { name: 'units', type: 'INT', description: '销售数量' },
      { name: 'transaction_price', type: 'DECIMAL', description: '实际成交价（元）' },
      { name: 'msrp', type: 'DECIMAL', description: '厂商指导价（元）' },
    ],
  },
  {
    name: 'fact_marketing_spend',
    fullName: '营销投放事实表',
    description: '记录各渠道的营销费用与产生的线索数据，用于 CPL 与 ROI 分析',
    icon: '📢',
    rows: '约 1,200 行',
    columns: [
      { name: 'spend_id', type: 'VARCHAR', description: '投放记录 ID（主键）', pk: true },
      { name: 'spend_date', type: 'DATE', description: '投放日期' },
      { name: 'channel_code', type: 'VARCHAR', description: '渠道编码（抖音/百度等）' },
      { name: 'brand_code', type: 'VARCHAR', description: '品牌编码' },
      { name: 'spend_amount', type: 'DECIMAL', description: '投放金额（元）' },
      { name: 'impressions', type: 'INT', description: '曝光量' },
      { name: 'clicks', type: 'INT', description: '点击量' },
      { name: 'leads', type: 'INT', description: '有效线索数' },
    ],
  },
  {
    name: 'fact_dealer_traffic',
    fullName: '门店客流事实表',
    description: '记录经销商门店的客流与转化数据，用于漏斗分析',
    icon: '🏪',
    rows: '约 3,400 行',
    columns: [
      { name: 'traffic_id', type: 'VARCHAR', description: '客流记录 ID（主键）', pk: true },
      { name: 'record_date', type: 'DATE', description: '记录日期' },
      { name: 'dealer_id', type: 'VARCHAR', description: '经销商 ID' },
      { name: 'brand_code', type: 'VARCHAR', description: '品牌编码' },
      { name: 'region_code', type: 'VARCHAR', description: '大区编码' },
      { name: 'visits', type: 'INT', description: '进店客流量' },
      { name: 'test_drive_count', type: 'INT', description: '试驾次数' },
      { name: 'orders', type: 'INT', description: '成交订单数' },
    ],
  },
  {
    name: 'dim_budget_target',
    fullName: '预算目标维度表',
    description: '按品牌 × 月份的预算目标，与销售事实表关联用于达成率分析',
    icon: '🎯',
    rows: '约 120 行',
    columns: [
      { name: 'brand_code', type: 'VARCHAR', description: '品牌编码', pk: true },
      { name: 'year_month', type: 'VARCHAR', description: '年月（YYYY-MM）', pk: true },
      { name: 'target_units', type: 'INT', description: '目标交付量' },
      { name: 'target_revenue', type: 'DECIMAL', description: '目标营收（元）' },
    ],
  },
];

export default function TablesPage() {
  return (
    <div className="content-wrap">
      {/* 顶部说明 */}
      <div className="content-card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0"><GacBadge size="lg" /></div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gac-gray-900 mb-1">数据表</h2>
            <p className="text-sm text-gac-gray-500 leading-relaxed">
              系统底层基于 DuckDB 引擎，包含
              <span className="font-semibold text-gac-primary"> {TABLES.length} 张</span>
              核心表：3 张事实表 + 1 张维度表。所有 SQL 查询严格遵循只读原则。
            </p>
          </div>
        </div>
      </div>

      {/* 数据表卡片 */}
      <div className="space-y-4">
        {TABLES.map((t) => (
          <div key={t.name} className="content-card overflow-hidden">
            {/* 表头 */}
            <div className="p-5 border-b border-gac-gray-200 bg-gradient-to-r from-blue-50/50 to-transparent">
              <div className="flex items-center gap-3 mb-2">
                <div className="text-3xl">{t.icon}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-gac-gray-900 font-mono">
                      {t.name}
                    </h3>
                    <span className="text-xs px-2 py-0.5 bg-gac-primary text-white rounded">
                      DuckDB
                    </span>
                  </div>
                  <p className="text-sm text-gac-gray-500 mt-1">{t.fullName} · {t.rows}</p>
                </div>
                <code className="text-xs bg-slate-900 text-green-400 px-3 py-2 rounded font-mono">
                  SELECT * FROM {t.name} LIMIT 10
                </code>
              </div>
              <p className="text-sm text-gac-gray-700 leading-relaxed">{t.description}</p>
            </div>

            {/* 字段表 */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gac-gray-50 border-b border-gac-gray-200">
                  <tr>
                    <th className="px-5 py-3 text-left font-semibold text-gac-gray-700 w-1/4">字段名</th>
                    <th className="px-5 py-3 text-left font-semibold text-gac-gray-700 w-1/6">类型</th>
                    <th className="px-5 py-3 text-left font-semibold text-gac-gray-700">说明</th>
                  </tr>
                </thead>
                <tbody>
                  {t.columns.map((col) => (
                    <tr key={col.name} className="border-b border-gac-gray-100 hover:bg-gac-gray-50">
                      <td className="px-5 py-3 font-mono text-gac-primary">
                        {col.name}
                        {col.pk && <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">PK</span>}
                      </td>
                      <td className="px-5 py-3 font-mono text-xs text-gac-gray-700">{col.type}</td>
                      <td className="px-5 py-3 text-gac-gray-700">{col.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
