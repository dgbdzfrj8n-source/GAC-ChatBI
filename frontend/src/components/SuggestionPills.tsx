"use client";

import { MessageCircle } from "lucide-react";

interface SuggestionPillsProps {
  onSuggestion: (text: string) => void;
}

const SUGGESTIONS = [
  { icon: "🔥", text: "2025年3月埃安销量与预算达成率是多少？" },
  { icon: "📊", text: "各品牌总交付量与总营收是多少？" },
  { icon: "💰", text: "各营销渠道投放支出与获客成本CPL排名" },
  { icon: "🚗", text: "传祺各车型在华东大区的销量" },
  { icon: "📈", text: "2025年Q1各月交付量走势" },
  { icon: "🎯", text: "昊铂GT与昊铂HT客流转化率对比" },
];

export default function SuggestionPills({ onSuggestion }: SuggestionPillsProps) {
  return (
    <div className="flex flex-wrap gap-2 items-center">
      <div className="flex items-center gap-1.5 mr-1 text-xs text-gray-400">
        <MessageCircle className="w-3.5 h-3.5" />
        <span className="font-medium">快捷提问：</span>
      </div>
      {SUGGESTIONS.map((s, i) => (
        <button
          key={i}
          onClick={() => onSuggestion(s.text)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs
                     bg-white border border-gray-200 text-gray-600
                     hover:border-emerald-400 hover:text-emerald-700 hover:bg-emerald-50
                     transition-all duration-200 shadow-sm
                     active:scale-95 cursor-pointer"
        >
          <span>{s.icon}</span>
          <span className="whitespace-nowrap">{s.text.length > 20 ? s.text.slice(0, 20) + "..." : s.text}</span>
        </button>
      ))}
    </div>
  );
}
