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

// v2.0 快捷提问列表（20条，新增库存管理分类）
const SUGGESTIONS_V2: Suggestion[] = [
  // ===== 整车销售（6条）=====
  { id: 'Q01', label: '2025年3月埃安销量与预算达成率是多少？', domain: '整车销售', chart_hint: 'table', icon: '🚗' },
  { id: 'Q02', label: '各品牌总交付量与总营收是多少？', domain: '整车销售', chart_hint: 'bar', icon: '🚗' },
  { id: 'Q03', label: '传祺各车型在华东大区的销量', domain: '整车销售', chart_hint: 'bar', icon: '🚗' },
  { id: 'Q04', label: '2025年Q1各月交付量走势', domain: '整车销售', chart_hint: 'line', icon: '🚗' },
  { id: 'Q05', label: '昊铂GT与昊铂HT客流转化率对比', domain: '整车销售', chart_hint: 'bar', icon: '🚗' },
  { id: 'Q06', label: '销量环比下降最多的品牌', domain: '整车销售', chart_hint: 'table', icon: '🚗' },
  
  // ===== 经营财务（3条）=====
  { id: 'Q07', label: '各品牌单车成交均价对比', domain: '经营财务', chart_hint: 'bar', icon: '💰' },
  { id: 'Q08', label: '投放金额最高的渠道', domain: '经营财务', chart_hint: 'pie', icon: '💰' },
  { id: 'Q09', label: '单车毛利贡献最高的车型', domain: '经营财务', chart_hint: 'bar', icon: '💰' },
  
  // ===== 市场营销（3条）=====
  { id: 'Q10', label: '各营销渠道投放支出与获客成本CPL排名', domain: '市场营销', chart_hint: 'bar', icon: '📢' },
  { id: 'Q11', label: '抖音线索量占总线索量多少', domain: '市场营销', chart_hint: 'pie', icon: '📢' },
  { id: 'Q12', label: '各渠道ROI对比', domain: '市场营销', chart_hint: 'bar', icon: '📢' },
  
  // ===== 渠道经营（3条）=====
  { id: 'Q13', label: '各大区客流成交转化率排名', domain: '渠道经营', chart_hint: 'bar', icon: '🏪' },
  { id: 'Q14', label: '客流漏斗：进店→试驾→成交', domain: '渠道经营', chart_hint: 'funnel', icon: '🏪' },
  { id: 'Q15', label: '转化率低于10%的大区', domain: '渠道经营', chart_hint: 'table', icon: '🏪' },
  
  // ===== 库存管理（5条）【v2.0新增】=====
  { id: 'Q16', label: '华东大区客流成交转化率排名？', domain: '库存管理', chart_hint: 'bar', icon: '📦' },
  { id: 'Q17', label: '进店→留资→试驾→成交的客流漏斗', domain: '库存管理', chart_hint: 'funnel', icon: '📦' },
  { id: 'Q18', label: '当前库存周转天数最高的车型？', domain: '库存管理', chart_hint: 'bar', icon: '📦' },
  { id: 'Q19', label: '库存系数超过2.0的高库存预警车型', domain: '库存管理', chart_hint: 'table', icon: '📦' },
  { id: 'Q20', label: '抖音渠道的留资率比自然到店高多少？', domain: '库存管理', chart_hint: 'bar', icon: '📦' },
];

export default function SuggestionPills({ onSuggestion }: SuggestionPillsProps) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>(SUGGESTIONS_V2);
  const [domain, setDomain] = useState<string>('全部');

  useEffect(() => {
    // 尝试从后端获取快捷提问
    fetch(`${API_URL}/api/chat/quick-suggestions`)
      .then((r) => r.json())
      .then((d) => {
        if (d.suggestions && d.suggestions.length > 0) {
          setSuggestions(d.suggestions);
        }
      })
      .catch(() => {
        // 失败时使用内置数据
      });
  }, []);

  // v2.0: 5大业务域
  const domains = ['全部', '整车销售', '经营财务', '市场营销', '渠道经营', '库存管理'];
  const visible = domain === '全部' ? suggestions : suggestions.filter((s) => s.domain === domain);

  return (
    <div className="space-y-2">
      {/* 快捷提问标题 */}
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <MessageCircle className="w-3.5 h-3.5" />
          <span className="font-medium">
            快捷提问（{suggestions.length} 条 · 覆盖 5 大业务域 · 每条精准匹配 SQL 模板）
          </span>
        </div>
        {/* v2.0 新增标签 */}
        <span className="px-2 py-0.5 text-[10px] bg-blue-100 text-blue-700 rounded-full">
          v2.0 新增库存管理
        </span>
      </div>

      {/* 业务域切换（5个分类） */}
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
