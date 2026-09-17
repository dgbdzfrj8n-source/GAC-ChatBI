"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Loader2, FileText, X, BarChart3 } from "lucide-react";

export interface DimensionOption {
  id: string;
  label: string;
  desc: string;
}

export const DIMENSION_OPTIONS: DimensionOption[] = [
  { id: "brand_name",    label: "品牌维度",   desc: "广丰 / 广本 / 自主" },
  { id: "region_name",   label: "区域维度",   desc: "华南 / 华北 / 华东 / 华中" },
  { id: "model_name",    label: "车型维度",   desc: "轿车 / SUV / MPV" },
  { id: "energy_type",   label: "能源类型",   desc: "纯电 / 混动 / 燃油" },
  { id: "price_segment", label: "价格段维度", desc: "高价车 / 中价车 / 低价车" },
  { id: "monthly",       label: "时间维度",   desc: "周内波动 / 月初 vs 月末" },
];

// ⭐ P1：归因指标选项（前后端 5 个固定值必须保持一致）
interface MetricOption {
  key: string;
  label: string;
  unit: string;
  description: string;
  applicable_dimensions: string[];
}

const FALLBACK_METRICS: MetricOption[] = [
  { key: "delivered_units", label: "总交付量", unit: "辆", description: "整车交付数（核心销量口径）", applicable_dimensions: ["brand_name","region_name","model_name","energy_type","price_segment","monthly"] },
  { key: "gross_revenue",   label: "总营收",   unit: "元", description: "开票总营收（财务口径）",     applicable_dimensions: ["brand_name","region_name","model_name","energy_type","price_segment"] },
  { key: "customer_leads",  label: "进店线索量", unit: "条", description: "进店/留资意向客户数",      applicable_dimensions: ["brand_name","region_name","model_name","energy_type","monthly"] },
  { key: "conversion_rate", label: "客流转化率", unit: "%", description: "交付量/线索量（终端效率）", applicable_dimensions: ["brand_name","region_name","model_name","price_segment"] },
  { key: "avg_price",       label: "单车成交均价", unit: "元/辆", description: "营收/交付量（产品结构）", applicable_dimensions: ["brand_name","region_name","model_name","energy_type","price_segment"] },
];

interface Template {
  id: string;
  name: string;
  description: string;
  scope: "system" | "user";
  dimensions: string[];
}

interface DimensionPickerProps {
  defaultSelected?: string[];
  maxSelect?: number;
  loading?: boolean;
  onConfirm: (selected: string[], metricKey: string) => void;  // ⭐ P1：回调带上 metric_key
  onCancel: () => void;
  currentRole?: string;
  currentUser?: string;
  initialMetricKey?: string;          // ⭐ P1：外部传入初始指标（如模板驱动）
}

const DIMENSION_LABELS: Record<string, string> = {
  brand_name: "品牌", region_name: "区域", model_name: "车型",
  energy_type: "能源", price_segment: "价格段", monthly: "时间",
};

export default function DimensionPicker({
  defaultSelected,
  maxSelect = 4,
  loading = false,
  onConfirm,
  onCancel,
  currentRole = "executive",
  currentUser = "admin",
  initialMetricKey = "delivered_units",
}: DimensionPickerProps) {
  const [selected, setSelected] = useState<string[]>(
    defaultSelected || ["brand_name", "region_name", "model_name"]
  );
  const [templates, setTemplates] = useState<Template[]>([]);
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);
  const [templateOpen, setTemplateOpen] = useState(false);
  // ⭐ P1：归因指标（默认 delivered_units，可由外部模板覆盖）
  const [metricKey, setMetricKey] = useState<string>(initialMetricKey);
  const [metrics, setMetrics] = useState<MetricOption[]>(FALLBACK_METRICS);
  const [metricAutoPruned, setMetricAutoPruned] = useState<{ from: string; removed: string[] } | null>(null);

  // ⭐ P1：当前指标对应的可用维度集合
  const currentMetric = metrics.find((m) => m.key === metricKey) || FALLBACK_METRICS[0];
  const allowedDimSet = new Set(currentMetric.applicable_dimensions);

  // 加载模板列表 + 自动应用角色默认模板
  useEffect(() => {
    const load = async () => {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const [tplRes, metricRes] = await Promise.all([
          fetch(`${API_URL}/api/sop/templates?role=${currentRole}&user=${currentUser}`),
          fetch(`${API_URL}/api/sop/supported-metrics`).catch(() => null),
        ]);
        if (tplRes.ok) {
          const data = await tplRes.json();
          const all = [...(data.system_presets || []), ...(data.user_templates || [])];
          setTemplates(all);
          // 自动应用角色默认模板
          if (data.role_default_id) {
            const defaultTpl = all.find((t: Template) => t.id === data.role_default_id);
            if (defaultTpl) {
              setSelected(defaultTpl.dimensions);
              setActiveTemplateId(defaultTpl.id);
              // ⭐ P1：模板携带 metric_key 时也应用
              if (defaultTpl.metric_key) {
                setMetricKey(defaultTpl.metric_key);
              }
            }
          }
        }
        if (metricRes && metricRes.ok) {
          const m = await metricRes.json();
          if (Array.isArray(m.metrics) && m.metrics.length > 0) {
            setMetrics(m.metrics);
          }
        }
      } catch (e) {
        console.warn("Failed to load templates/metrics:", e);
      }
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRole, currentUser]);

  // ⭐ P1：切换指标时，按新指标的 applicable_dimensions 过滤已选维度
  const handleMetricChange = (newKey: string) => {
    const newMetric = metrics.find((m) => m.key === newKey) || FALLBACK_METRICS.find((m) => m.key === newKey);
    if (!newMetric) return;
    setMetricKey(newKey);
    setMetricAutoPruned(null);  // 清除旧提示
    const newAllowed = new Set(newMetric.applicable_dimensions);
    const filtered = selected.filter((d) => newAllowed.has(d));
    if (filtered.length !== selected.length) {
      const removed = selected.filter((d) => !newAllowed.has(d));
      setSelected(filtered);
      setMetricAutoPruned({ from: newMetric.label, removed });
    }
  };

  const toggle = (id: string) => {
    // 用户手动改了就清掉"激活模板"标记
    setActiveTemplateId(null);
    setMetricAutoPruned(null);
    if (selected.includes(id)) {
      setSelected(selected.filter((s) => s !== id));
    } else if (selected.length < maxSelect) {
      // ⭐ P1：不在当前指标适用范围内的维度不允许勾选
      if (!allowedDimSet.has(id)) return;
      setSelected([...selected, id]);
    }
  };

  const applyTemplate = (tpl: Template) => {
    setSelected(tpl.dimensions.slice(0, maxSelect));
    setActiveTemplateId(tpl.id);
    setTemplateOpen(false);
  };

  const clearTemplate = () => {
    setActiveTemplateId(null);
  };

  const activeTemplate = templates.find((t) => t.id === activeTemplateId);

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[60] flex items-center justify-center p-6 animate-fade-in"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-indigo-50">
          <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
            <span className="text-xl">🎯</span>
            选择归因维度
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            可使用下方模板快速套用，或手动勾选（最多 {maxSelect} 个）
          </p>
        </div>

        {/* ⭐ P1：归因指标选择器 */}
        <div className="px-6 py-3 border-b border-gray-100 bg-blue-50/40">
          <label className="flex items-center gap-2 text-xs font-medium text-gray-700 mb-1.5">
            <BarChart3 className="w-3.5 h-3.5 text-blue-500" />
            归因指标 <span className="text-red-500">*</span>
          </label>
          <select
            value={metricKey}
            onChange={(e) => handleMetricChange(e.target.value)}
            disabled={loading}
            className="w-full px-3 py-1.5 bg-white border border-gray-200 rounded-md text-sm focus:outline-none focus:border-blue-400"
          >
            {metrics.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}（{m.unit}）· {m.description}
              </option>
            ))}
          </select>
          {metricAutoPruned && metricAutoPruned.removed.length > 0 && (
            <div className="mt-1.5 text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              ⚠ 已自动剔除不适用于「{metricAutoPruned.from}」的维度：{metricAutoPruned.removed.map((d) => DIMENSION_LABELS[d] || d).join("、")}
            </div>
          )}
        </div>

        {/* 模板下拉 */}
        <div className="px-6 py-3 border-b border-gray-100 bg-gray-50">
          <div className="relative">
            <button
              onClick={() => setTemplateOpen(!templateOpen)}
              disabled={loading}
              className="w-full flex items-center justify-between gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg hover:border-purple-300 transition-colors text-sm"
            >
              <span className="flex items-center gap-2 min-w-0 flex-1">
                <FileText className="w-4 h-4 text-purple-500 flex-shrink-0" />
                {activeTemplate ? (
                  <>
                    <span className="font-medium text-gray-900 truncate">{activeTemplate.name}</span>
                    <span className="text-xs text-gray-400 truncate">
                      · {activeTemplate.dimensions.length} 个维度
                    </span>
                  </>
                ) : (
                  <span className="text-gray-500">📋 使用模板快速套用...</span>
                )}
              </span>
              {activeTemplate && (
                <span
                  role="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    clearTemplate();
                  }}
                  className="p-0.5 hover:bg-gray-100 rounded"
                >
                  <X className="w-3.5 h-3.5 text-gray-400" />
                </span>
              )}
              <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${templateOpen ? "rotate-180" : ""}`} />
            </button>

            {templateOpen && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-10 max-h-72 overflow-y-auto">
                {templates.length === 0 ? (
                  <div className="px-4 py-3 text-xs text-gray-400 text-center">
                    暂无模板
                  </div>
                ) : (
                  templates.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => applyTemplate(t)}
                      className={`w-full text-left px-4 py-2.5 hover:bg-purple-50 transition-colors border-b border-gray-50 last:border-0 ${
                        activeTemplateId === t.id ? "bg-purple-50" : ""
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-sm text-gray-900 truncate">
                          {t.name}
                        </span>
                        <span className="text-[10px] text-gray-400 flex-shrink-0">
                          {t.scope === "system" ? "🔒 系统" : "✏️ 我的"}
                        </span>
                      </div>
                      {t.description && (
                        <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                          {t.description}
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1 mt-1">
                        {t.dimensions.map((d) => (
                          <span
                            key={d}
                            className="inline-block px-1.5 py-0.5 bg-gray-100 text-gray-600 text-[10px] rounded"
                          >
                            {DIMENSION_LABELS[d] || d}
                          </span>
                        ))}
                      </div>
                    </button>
                  ))
                )}
                <div className="px-4 py-2 border-t border-gray-100 bg-gray-50 text-center">
                  <a
                    href="/templates"
                    className="text-xs text-purple-600 hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    管理我的模板 →
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Body：维度勾选 */}
        <div className="px-6 py-4 space-y-2 overflow-y-auto flex-1">
          {DIMENSION_OPTIONS.map((dim) => {
            const isSelected = selected.includes(dim.id);
            const dimAllowed = allowedDimSet.has(dim.id);
            const disabled = !dimAllowed || (!isSelected && selected.length >= maxSelect);
            return (
              <label
                key={dim.id}
                className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                  !dimAllowed
                    ? "opacity-40 cursor-not-allowed border-gray-100 bg-gray-50"
                    : isSelected
                      ? "border-purple-400 bg-purple-50 ring-1 ring-purple-200 cursor-pointer"
                      : disabled
                        ? "border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed"
                        : "border-gray-200 hover:border-gray-300 hover:bg-gray-50 cursor-pointer"
                }`}
                title={!dimAllowed ? `「${currentMetric.label}」指标下不适用此维度` : ""}
              >
                <input
                  type="checkbox"
                  className="w-4 h-4 text-purple-600 rounded"
                  checked={isSelected}
                  disabled={disabled}
                  onChange={() => toggle(dim.id)}
                />
                <div className="flex-1">
                  <div className="font-medium text-sm text-gray-900">{dim.label}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{dim.desc}</div>
                </div>
                {!dimAllowed ? (
                  <span className="text-[10px] px-2 py-0.5 bg-gray-100 text-gray-400 rounded-full font-medium">
                    不适用
                  </span>
                ) : isSelected ? (
                  <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full font-medium">
                    已选
                  </span>
                ) : null}
              </label>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex gap-3 flex-shrink-0">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 py-2 text-sm border border-gray-300 rounded-lg hover:bg-white transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={() => onConfirm(selected, metricKey)}
            disabled={loading || selected.length === 0}
            className="flex-1 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 font-medium flex items-center justify-center gap-1"
          >
            {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {loading ? "启动 SOP..." : `开始分析（${selected.length} 个维度）`}
          </button>
        </div>
      </div>
    </div>
  );
}
