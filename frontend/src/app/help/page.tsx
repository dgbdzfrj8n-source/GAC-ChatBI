'use client';

import GacLogo from '@/components/GacLogo';

interface FaqItem {
  q: string;
  a: string;
}

const FAQS: FaqItem[] = [
  {
    q: '广汽云 ChatBI 是什么？',
    a: '广汽云 ChatBI 是广汽集团智能经营分析团队自研的 AI 问数平台，基于真实经营数据，通过自然语言对话方式快速获取经营指标与归因分析结果。',
  },
  {
    q: '支持哪些品牌的数据？',
    a: '目前支持广汽埃安、广汽传祺、昊铂 3 大品牌，覆盖整车销售、经营财务、市场营销、渠道经营 4 大业务域。',
  },
  {
    q: '查询响应有多快？',
    a: '基于 DuckDB 内存引擎与 Schema 动态剪枝，简单查询首字延迟 < 600ms，复杂查询 1-3 秒返回。',
  },
  {
    q: '数据是真实的吗？',
    a: '采用高仿真 Mock 数据（2 万+ 条记录），严格遵循广汽集团实际业务口径，可作为产品演示与方案验证使用。',
  },
  {
    q: '如何使用驾驶舱大屏？',
    a: '点击左侧菜单"驾驶舱大屏"即可进入，查看 4 个核心 KPI 卡片 + 趋势图 + 品牌排名 + 异常预警。',
  },
];

const GUIDES = [
  { icon: '1️⃣', title: '输入问题', desc: '在底部输入框用自然语言描述您的经营分析需求，例如"2025年3月埃安销量"' },
  { icon: '2️⃣', title: 'AI 自动分析', desc: '系统识别意图、检索 Schema、生成 SQL、自动选择图表类型，全程流式输出' },
  { icon: '3️⃣', title: '查看结果', desc: '可查看图表、数据表、SQL 代码、思考链，支持一键复制与深度归因' },
  { icon: '4️⃣', title: '钉入驾驶舱', desc: '高频指标可一键钉入驾驶舱大屏，下次直接查看' },
];

export default function HelpPage() {
  return (
    <div className="max-w-4xl">
      {/* 顶部说明 */}
      <div className="content-card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0"><GacLogo size="lg" /></div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gac-gray-900 mb-1">帮助文档</h2>
            <p className="text-sm text-gac-gray-500 leading-relaxed">
              快速上手广汽云 ChatBI，包含使用指南、常见问题与最佳实践。
            </p>
          </div>
        </div>
      </div>

      {/* 使用指南 */}
      <div className="content-card p-5 mb-4">
        <h3 className="text-sm font-semibold text-gac-gray-900 mb-4 flex items-center">
          <span className="w-1 h-4 bg-gac-primary rounded mr-2"></span>
          🚀 4 步快速上手
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {GUIDES.map((g) => (
            <div key={g.title} className="flex items-start gap-3 p-3 bg-gac-gray-50 rounded-lg">
              <div className="text-2xl">{g.icon}</div>
              <div>
                <div className="font-semibold text-gac-gray-900 text-sm mb-1">{g.title}</div>
                <div className="text-xs text-gac-gray-500 leading-relaxed">{g.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 快捷提问示例 */}
      <div className="content-card p-5 mb-4">
        <h3 className="text-sm font-semibold text-gac-gray-900 mb-4 flex items-center">
          <span className="w-1 h-4 bg-gac-primary rounded mr-2"></span>
          💡 快捷提问示例
        </h3>
        <div className="space-y-2">
          {[
            '🔥 2025年3月埃安销量与预算达成率是多少？',
            '📊 各品牌总交付量与总营收是多少？',
            '💰 各营销渠道投放支出与获客成本 CPL 排名',
            '🚗 传祺各车型在华东大区的销量',
            '📈 2025年Q1各月交付量走势',
            '🎯 昊铂 GT 与昊铂 HT 客流转化率对比',
          ].map((q, i) => (
            <div
              key={i}
              className="px-3 py-2 bg-gac-gray-50 hover:bg-blue-50 rounded text-sm text-gac-gray-700 cursor-pointer transition-colors"
            >
              {q}
            </div>
          ))}
        </div>
      </div>

      {/* FAQ */}
      <div className="content-card p-5">
        <h3 className="text-sm font-semibold text-gac-gray-900 mb-4 flex items-center">
          <span className="w-1 h-4 bg-gac-primary rounded mr-2"></span>
          ❓ 常见问题
        </h3>
        <div className="space-y-2">
          {FAQS.map((f, i) => (
            <details key={i} className="group border border-gac-gray-200 rounded-lg overflow-hidden">
              <summary className="cursor-pointer px-4 py-3 bg-white hover:bg-gac-gray-50 text-sm font-medium text-gac-gray-900 list-none flex items-center justify-between">
                <span>{f.q}</span>
                <span className="text-gac-gray-400 group-open:rotate-180 transition-transform flex-shrink-0 ml-2">▼</span>
              </summary>
              <div className="px-4 py-3 text-sm text-gac-gray-700 leading-relaxed bg-gac-gray-50 border-t border-gac-gray-200">
                {f.a}
              </div>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
}
