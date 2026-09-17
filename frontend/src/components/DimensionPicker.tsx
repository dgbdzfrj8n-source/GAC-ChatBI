"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Loader2, FileText, X } from "lucide-react";

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
  onConfirm: (selected: string[]) => void;
  onCancel: () => void;
  currentRole?: string;
  currentUser?: string;
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
}: DimensionPickerProps) {
  const [selected, setSelected] = useState<string[]>(
    defaultSelected || ["brand_name", "region_name", "model_name"]
  );
  const [templates, setTemplates] = useState<Template[]>([]);
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);
  const [templateOpen, setTemplateOpen] = useState(false);

  // 加载模板列表 + 自动应用角色默认模板
  useEffect(() => {
    const load = async () => {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(
          `${API_URL}/api/sop/templates?role=${currentRole}&user=${currentUser}`
        );
        if (res.ok) {
          const data = await res.json();
          const all = [...(data.system_presets || []), ...(data.user_templates || [])];
          setTemplates(all);
          // 自动应用角色默认模板
          if (data.role_default_id) {
            const defaultTpl = all.find((t: Template) => t.id === data.role_default_id);
            if (defaultTpl) {
              setSelected(defaultTpl.dimensions);
              setActiveTemplateId(defaultTpl.id);
            }
          }
        }
      } catch (e) {
        console.warn("Failed to load templates:", e);
      }
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRole, currentUser]);

  const toggle = (id: string) => {
    // 用户手动改了就清掉"激活模板"标记
    setActiveTemplateId(null);
    if (selected.includes(id)) {
      setSelected(selected.filter((s) => s !== id));
    } else if (selected.length < maxSelect) {
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
            const disabled = !isSelected && selected.length >= maxSelect;
            return (
              <label
                key={dim.id}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? "border-purple-400 bg-purple-50 ring-1 ring-purple-200"
                    : disabled
                      ? "border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                }`}
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
                {isSelected && (
                  <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full font-medium">
                    已选
                  </span>
                )}
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
            onClick={() => onConfirm(selected)}
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
