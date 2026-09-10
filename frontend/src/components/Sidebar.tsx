"use client";

import { useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  DollarSign,
  Users,
  Target,
  BarChart2,
  Database,
  Clock,
  CheckCircle2,
} from "lucide-react";

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

const METRIC_GROUPS = [
  {
    group: "整车销售",
    icon: TrendingUp,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    metrics: [
      { id: "M01", name: "销售达成率", unit: "%" },
      { id: "M02", name: "总交付量", unit: "辆" },
      { id: "M03", name: "单车成交均价", unit: "元/辆" },
    ],
  },
  {
    group: "经营财务",
    icon: DollarSign,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    metrics: [{ id: "M04", name: "单车营销费用", unit: "元/辆" }],
  },
  {
    group: "市场营销",
    icon: BarChart2,
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    metrics: [{ id: "M05", name: "单渠道获客成本(CPL)", unit: "元/条" }],
  },
  {
    group: "渠道经营",
    icon: Users,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    metrics: [{ id: "M06", name: "客流成交转化率", unit: "%" }],
  },
];

const TABLES = [
  { name: "fact_sales_daily", desc: "整车销售交付事实表", rows: "19,440 行" },
  { name: "dim_budget_target", desc: "集团经营预算目标表", rows: "48 行" },
  { name: "fact_marketing_expenses", desc: "市场营销获客支出表", rows: "5,832 行" },
];

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const [activeTab, setActiveTab] = useState<"metrics" | "tables" | "history">("metrics");

  if (!isOpen) {
    return (
      <div className="border-r border-gray-200 bg-white">
        <button
          onClick={onToggle}
          className="w-full h-12 flex items-center justify-center hover:bg-gray-50 transition-colors"
          title="展开侧边栏"
        >
          <ChevronRight className="w-5 h-5 text-gray-400" />
        </button>
      </div>
    );
  }

  return (
    <aside className="w-72 border-r border-gray-200 bg-white flex flex-col animate-slide-up">
      {/* 折叠按钮 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">业务资产</span>
        <button
          onClick={onToggle}
          className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-gray-100 transition-colors"
          title="收起侧边栏"
        >
          <ChevronLeft className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* Tab 切换 */}
      <div className="flex border-b border-gray-200">
        {[
          { id: "metrics", label: "指标库", icon: Target },
          { id: "tables", label: "数据表", icon: Database },
          { id: "history", label: "历史会话", icon: Clock },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-all ${
              activeTab === tab.id
                ? "text-emerald-600 border-b-2 border-emerald-500 -mb-px"
                : "text-gray-400 hover:text-gray-600"
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 指标库 */}
        {activeTab === "metrics" && (
          <>
            {METRIC_GROUPS.map((group) => (
              <div key={group.group}>
                <div className={`flex items-center gap-2 mb-2 px-2`}>
                  <group.icon className={`w-4 h-4 ${group.color}`} />
                  <span className="text-xs font-semibold text-gray-600">{group.group}</span>
                </div>
                <div className="space-y-1">
                  {group.metrics.map((m) => (
                    <div
                      key={m.id}
                      className={`flex items-center justify-between px-3 py-2 rounded-lg ${group.bgColor} hover:opacity-80 transition-opacity cursor-pointer`}
                    >
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className={`w-3.5 h-3.5 ${group.color} opacity-60`} />
                        <span className="text-xs text-gray-700">{m.name}</span>
                      </div>
                      <span className={`text-xs ${group.color} font-mono`}>{m.unit}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </>
        )}

        {/* 数据表 */}
        {activeTab === "tables" && (
          <div className="space-y-2">
            {TABLES.map((t) => (
              <div
                key={t.name}
                className="p-3 rounded-xl border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/30 transition-all cursor-pointer"
              >
                <div className="flex items-start gap-2">
                  <Database className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs font-mono text-gray-800 font-medium truncate">{t.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{t.desc}</p>
                    <p className="text-xs text-gray-400 mt-1 font-mono">{t.rows}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 历史会话 */}
        {activeTab === "history" && (
          <div className="text-center py-12">
            <Clock className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-400">暂无历史会话记录</p>
            <p className="text-xs text-gray-300 mt-1">开始提问后将自动保存</p>
          </div>
        )}
      </div>
    </aside>
  );
}
