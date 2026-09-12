'use client';

import { MessageCircle } from "lucide-react";

interface SuggestionPillsProps {
  onSuggestion: (text: string) => void;
}

// 扩充至 15+ 条，覆盖 4 大业务域（整车销售 / 经营财务 / 市场营销 / 渠道经营）
const SUGGESTIONS = [
  // === 整车销售（6条）===
  { icon: "🔥", text: "2025年3月埃安销量与预算达成率是多少？", domain: "整车销售" },
  { icon: "📊", text: "各品牌总交付量与总营收是多少？", domain: "整车销售" },
  { icon: "🚗", text: "传祺各车型在华东大区的销量", domain: "整车销售" },
  { icon: "📈", text: "2025年Q1各月交付量走势", domain: "整车销售" },
  { icon: "🏆", text: "昊铂GT与昊铂HT客流转化率对比", domain: "整车销售" },
  { icon: "📉", text: "销量环比下降最多的品牌", domain: "整车销售" },

  // === 经营财务（3条）===
  { icon: "💰", text: "各品牌单车成交均价对比", domain: "经营财务" },
  { icon: "📉", text: "营销费用占比最高的渠道", domain: "经营财务" },
  { icon: "💵", text: "毛利率最高的是哪个车型", domain: "经营财务" },

  // === 市场营销（3条）===
  { icon: "💰", text: "各营销渠道投放支出与获客成本CPL排名", domain: "市场营销" },
  { icon: "📢", text: "抖音线索量占总线索量多少", domain: "市场营销" },
  { icon: "🎯", text: "各渠道ROI对比", domain: "市场营销" },

  // === 渠道经营（3条）===
  { icon: "🏪", text: "各门店客流成交转化率排名", domain: "渠道经营" },
  { icon: "📊", text: "客流漏斗：进店→留资→试驾→成交", domain: "渠道经营" },
  { icon: "⚠️", text: "转化率低于10%的门店", domain: "渠道经营" },
];

export default function SuggestionPills({ onSuggestion }: SuggestionPillsProps) {
  return (
    <div className="space-y-2">
      {/* 快捷提问标题 */}
      <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-1">
        <MessageCircle className="w-3.5 h-3.5" />
        <span className="font-medium">快捷提问（{SUGGESTIONS.length} 条，覆盖 4 大业务域）</span>
      </div>

      {/* 快捷提问按钮 */}
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onSuggestion(s.text)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs
                       bg-white border border-gray-200 text-gray-600
                       hover:border-gac-primary hover:text-gac-primary hover:bg-blue-50
                       transition-all duration-200 shadow-sm
                       active:scale-95 cursor-pointer"
            title={`[${s.domain}] ${s.text}`}
          >
            <span>{s.icon}</span>
            <span className="whitespace-nowrap">
              {s.text.length > 22 ? s.text.slice(0, 22) + "..." : s.text}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
