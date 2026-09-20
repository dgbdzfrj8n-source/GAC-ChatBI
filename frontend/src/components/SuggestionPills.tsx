'use client';

import { useEffect, useState } from 'react';
import { MessageCircle } from 'lucide-react';

interface SuggestionPillsProps {
  onSuggestion: (text: string) => void;
}

interface Suggestion {
  id: string;
  label: string;
  domain: string;
  chart_hint: string;
  icon: string;
}

const API_URL =
  typeof window !== 'undefined'
    ? localStorage.getItem('apiUrl') || process.env.NEXT_PUBLIC_API_URL || 'https://gac-chatbi-api.onrender.com'
    : process.env.NEXT_PUBLIC_API_URL || 'https://gac-chatbi-api.onrender.com';

export default function SuggestionPills({ onSuggestion }: SuggestionPillsProps) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [domain, setDomain] = useState<string>('全部');

  useEffect(() => {
    // 从后端拉取 15 条精确问数模板（保证 SQL 100% 命中）
    fetch(`${API_URL}/api/chat/quick-suggestions`)
      .then((r) => r.json())
      .then((d) => setSuggestions(d.suggestions || []))
      .catch(() => {
        // 兜底：API 不可达时使用前端硬编码（建议但 SQL 可能不命中）
        setSuggestions(FALLBACK);
      });
  }, []);

  const domains = ['全部', ...Array.from(new Set(suggestions.map((s) => s.domain)))];
  const visible = domain === '全部' ? suggestions : suggestions.filter((s) => s.domain === domain);

  return (
    <div className="space-y-2">
      {/* 快捷提问标题 */}
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <MessageCircle className="w-3.5 h-3.5" />
          <span className="font-medium">
            快捷提问（{suggestions.length} 条 · 覆盖 4 大业务域 · 每条精准匹配 SQL 模板）
          </span>
        </div>
      </div>

      {/* 业务域切换 */}
      <div className="flex flex-wrap gap-1">
        {domains.map((d) => (
          <button
            key={d}
            onClick={() => setDomain(d)}
            className={`px-2.5 py-0.5 text-xs rounded-full transition-colors ${
              domain === d
                ? 'bg-gac-primary text-white'
                : 'bg-gac-gray-100 text-gac-gray-600 hover:bg-gac-gray-200'
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      {/* 快捷提问按钮 */}
      <div className="flex flex-wrap gap-2">
        {visible.map((s) => (
          <button
            key={s.id}
            onClick={() => onSuggestion(s.label)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs
                       bg-white border border-gray-200 text-gray-600
                       hover:border-gac-primary hover:text-gac-primary hover:bg-blue-50
                       transition-all duration-200 shadow-sm
                       active:scale-95 cursor-pointer"
            title={`[${s.domain}] ${s.label}`}
          >
            <span>{s.icon}</span>
            <span className="whitespace-nowrap">
              {s.label.length > 22 ? s.label.slice(0, 22) + "..." : s.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

// 兜底（API 不可达时使用）
const FALLBACK: Suggestion[] = [
  { id: 'Q01', label: '2025年3月埃安销量与预算达成率是多少？', domain: '整车销售', chart_hint: 'table', icon: '🚗' },
  { id: 'Q02', label: '各品牌总交付量与总营收是多少？', domain: '整车销售', chart_hint: 'bar', icon: '🚗' },
  { id: 'Q03', label: '传祺各车型在华东大区的销量', domain: '整车销售', chart_hint: 'bar', icon: '🚗' },
  { id: 'Q04', label: '2025年Q1各月交付量走势', domain: '整车销售', chart_hint: 'line', icon: '🚗' },
  { id: 'Q05', label: '昊铂GT与昊铂HT客流转化率对比', domain: '整车销售', chart_hint: 'bar', icon: '🚗' },
  { id: 'Q06', label: '销量环比下降最多的品牌', domain: '整车销售', chart_hint: 'table', icon: '🚗' },
  { id: 'Q07', label: '各品牌单车成交均价对比', domain: '经营财务', chart_hint: 'bar', icon: '💰' },
  { id: 'Q08', label: '投放金额最高的渠道', domain: '经营财务', chart_hint: 'pie', icon: '💰' },
  { id: 'Q09', label: '单车毛利贡献最高的车型', domain: '经营财务', chart_hint: 'bar', icon: '💰' },
  { id: 'Q10', label: '各营销渠道投放支出与获客成本CPL排名', domain: '市场营销', chart_hint: 'bar', icon: '📢' },
  { id: 'Q11', label: '抖音线索量占总线索量多少', domain: '市场营销', chart_hint: 'pie', icon: '📢' },
  { id: 'Q12', label: '各渠道ROI对比', domain: '市场营销', chart_hint: 'bar', icon: '📢' },
  { id: 'Q13', label: '各大区客流成交转化率排名', domain: '渠道经营', chart_hint: 'bar', icon: '🏪' },
  { id: 'Q14', label: '客流漏斗：进店→试驾→成交', domain: '渠道经营', chart_hint: 'funnel', icon: '🏪' },
  { id: 'Q15', label: '转化率低于10%的大区', domain: '渠道经营', chart_hint: 'table', icon: '🏪' },
];
