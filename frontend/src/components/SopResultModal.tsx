"use client";

import { X, Loader2, AlertTriangle, TrendingDown, Search, Lightbulb, BarChart3 } from "lucide-react";

interface SopResultModalProps {
  data: any;
  loading: boolean;
  onClose: () => void;
}

const STEP_LABELS: Record<number, { name: string; icon: any; color: string }> = {
  1: { name: "大盘对标", icon: TrendingDown, color: "text-red-500" },
  2: { name: "维度下钻", icon: Search, color: "text-orange-500" },
  3: { name: "跨域归因", icon: AlertTriangle, color: "text-amber-500" },
  4: { name: "策略建议", icon: Lightbulb, color: "text-emerald-500" },
};

export default function SopResultModal({ data, loading, onClose }: SopResultModalProps) {
  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-indigo-50">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">🔬</span>
              四步归因 SOP 分析报告
            </h2>
            <p className="text-xs text-gray-500 mt-1">
              大盘对标 → 维度下钻 → 跨域归因 → 策略建议
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-white/60 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-500">
              <Loader2 className="w-10 h-10 animate-spin text-purple-500 mb-3" />
              <p className="text-sm">正在执行四步归因 SOP...</p>
              <p className="text-xs text-gray-400 mt-1">通常耗时 1~2 秒</p>
            </div>
          ) : !data ? (
            <div className="text-center py-12 text-gray-400">暂无数据</div>
          ) : data.error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              ❌ 错误：{data.error}
            </div>
          ) : (
            <div className="space-y-6">
              {/* 核心指标 */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4 border border-purple-200">
                  <div className="text-xs text-purple-600 font-medium">达成率</div>
                  <div className="text-3xl font-bold text-purple-900 mt-1">
                    {data.fulfillment_rate_pct?.toFixed(2) || "0"}%
                  </div>
                </div>
                <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-xl p-4 border border-amber-200">
                  <div className="text-xs text-amber-600 font-medium">销量缺口</div>
                  <div className="text-3xl font-bold text-amber-900 mt-1">
                    {Math.abs(data.gap_units || 0).toLocaleString()}
                    <span className="text-sm font-normal text-amber-700 ml-1">辆</span>
                  </div>
                </div>
                <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-4 border border-slate-200">
                  <div className="text-xs text-slate-600 font-medium">评级</div>
                  <div className="text-2xl font-bold text-slate-900 mt-1">{data.gap_grade || "—"}</div>
                  <div className="text-[10px] text-slate-500 mt-1">{data.brand} · {data.year_month}</div>
                </div>
              </div>

              {/* 高管摘要 */}
              {data.executive_summary && (
                <div className="p-4 bg-gradient-to-r from-indigo-50 to-blue-50 rounded-xl border border-indigo-200">
                  <div className="text-xs font-semibold text-indigo-700 mb-2">📋 高管摘要</div>
                  <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed">
                    {data.executive_summary}
                  </pre>
                </div>
              )}

              {/* 四步详情 */}
              {Array.isArray(data.steps) && data.steps.length > 0 && (
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    SOP 详细步骤
                  </div>
                  {data.steps.map((step: any, idx: number) => {
                    const meta = STEP_LABELS[step.step] || STEP_LABELS[1];
                    const Icon = meta.icon;
                    return (
                      <div
                        key={idx}
                        className="border border-gray-200 rounded-xl p-4 hover:border-purple-300 transition-colors"
                      >
                        <div className="flex items-center gap-2 mb-3">
                          <div className={`w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center ${meta.color}`}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="font-semibold text-gray-900 text-sm">
                            第 {step.step} 步：{step.step_name || meta.name}
                          </div>
                        </div>
                        <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 rounded-lg p-3 max-h-48 overflow-y-auto">
                          {JSON.stringify(step, null, 2)}
                        </pre>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* 归因贡献明细（P0 新增：用户自定义归因维度后展示） */}
              {Array.isArray(data.attribution_breakdown) && data.attribution_breakdown.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    <BarChart3 className="w-3.5 h-3.5" />
                    <span>归因贡献明细</span>
                    {Array.isArray(data.selected_dimensions) && data.selected_dimensions.length > 0 && (
                      <span className="ml-auto text-[10px] font-normal text-purple-600 normal-case tracking-normal">
                        基于维度：{data.selected_dimensions
                          .map((k: string) => ({
                            brand_name: "品牌", region_name: "区域", model_name: "车型",
                            energy_type: "能源", price_segment: "价格段", monthly: "时间"
                          } as Record<string, string>)[k] || k)
                          .join(" / ")}
                      </span>
                    )}
                  </div>
                  <div className="border border-purple-200 rounded-xl overflow-hidden bg-gradient-to-br from-purple-50/30 to-white">
                    <table className="w-full text-sm">
                      <thead className="bg-purple-50 text-purple-900 text-xs">
                        <tr>
                          <th className="px-4 py-2 text-left font-medium">序号</th>
                          <th className="px-4 py-2 text-left font-medium">维度·成员</th>
                          <th className="px-4 py-2 text-right font-medium">贡献量</th>
                          <th className="px-4 py-2 text-right font-medium">占比</th>
                          <th className="px-4 py-2 text-left font-medium">归因推断</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 bg-white">
                        {data.attribution_breakdown.map((item: any, idx: number) => {
                          const contrib = item.contribution || 0;
                          const pct = item.contribution_pct || 0;
                          const isNegative = contrib < 0;
                          return (
                            <tr key={idx} className="hover:bg-purple-50/40 transition-colors">
                              <td className="px-4 py-2.5 text-gray-500 font-mono text-xs">
                                {idx === 0 ? "①" : idx === 1 ? "②" : idx === 2 ? "③" : (idx + 1)}
                              </td>
                              <td className="px-4 py-2.5">
                                <span className="inline-flex items-center gap-1.5">
                                  <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                                    {item.dimension_label}
                                  </span>
                                  <span className="font-medium text-gray-900">{item.member}</span>
                                </span>
                              </td>
                              <td className={`px-4 py-2.5 text-right font-mono font-semibold ${isNegative ? "text-red-600" : "text-emerald-600"}`}>
                                {contrib > 0 ? "+" : ""}{contrib.toLocaleString()}
                                <span className="text-xs text-gray-400 ml-1">辆</span>
                              </td>
                              <td className="px-4 py-2.5 text-right">
                                <div className="flex items-center justify-end gap-2">
                                  <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                    <div
                                      className={`h-full ${isNegative ? "bg-red-400" : "bg-emerald-400"}`}
                                      style={{ width: `${Math.min(Math.abs(pct), 100)}%` }}
                                    />
                                  </div>
                                  <span className={`text-xs font-mono ${isNegative ? "text-red-600" : "text-emerald-600"}`}>
                                    {pct > 0 ? "+" : ""}{pct.toFixed(1)}%
                                  </span>
                                </div>
                              </td>
                              <td className="px-4 py-2.5 text-xs text-gray-600">
                                {item.reason || "—"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot className="bg-gray-50 text-xs">
                        <tr>
                          <td colSpan={2} className="px-4 py-2 text-gray-500 font-medium">合计</td>
                          <td className="px-4 py-2 text-right font-mono font-bold text-gray-900">
                            {data.attribution_breakdown.reduce((s: number, x: any) => s + (x.contribution || 0), 0).toLocaleString()}
                            <span className="text-gray-500 ml-1">辆</span>
                          </td>
                          <td className="px-4 py-2 text-right font-mono font-bold text-gray-900">100%</td>
                          <td className="px-4 py-2 text-gray-400">— 各维度贡献量之和 = 指标总波动</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              )}

              {/* 策略建议卡片 */}
              {Array.isArray(data.recommendations) && data.recommendations.length > 0 && (
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    🎯 可执行策略建议
                  </div>
                  {data.recommendations.map((rec: any, idx: number) => {
                    const priorityColor =
                      rec.priority === "高"
                        ? "border-red-300 bg-red-50"
                        : rec.priority === "中"
                          ? "border-amber-300 bg-amber-50"
                          : "border-emerald-300 bg-emerald-50";
                    return (
                      <div key={idx} className={`border-l-4 ${priorityColor} rounded-r-xl p-4`}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-semibold text-gray-900 text-sm">
                            [{rec.type}] {rec.action}
                          </div>
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${rec.priority === "高"
                                ? "bg-red-200 text-red-800"
                                : rec.priority === "中"
                                  ? "bg-amber-200 text-amber-800"
                                  : "bg-emerald-200 text-emerald-800"
                              }`}
                          >
                            {rec.priority}优先
                          </span>
                        </div>
                        {rec.budget_impact && (
                          <div className="text-xs text-gray-600">
                            💰 预算影响：{rec.budget_impact}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {data.execution_time_ms !== undefined && (
                <div className="text-xs text-gray-400 text-right">
                  ⏱️ SOP 引擎耗时 {data.execution_time_ms} ms
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
