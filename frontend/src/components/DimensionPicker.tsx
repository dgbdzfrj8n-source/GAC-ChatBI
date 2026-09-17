"use client";

import { useState } from "react";

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

interface DimensionPickerProps {
  defaultSelected?: string[];
  maxSelect?: number;
  loading?: boolean;
  onConfirm: (selected: string[]) => void;
  onCancel: () => void;
}

export default function DimensionPicker({
  defaultSelected,
  maxSelect = 4,
  loading = false,
  onConfirm,
  onCancel,
}: DimensionPickerProps) {
  const [selected, setSelected] = useState<string[]>(
    defaultSelected || ["brand_name", "region_name", "model_name"]
  );

  const toggle = (id: string) => {
    if (selected.includes(id)) {
      setSelected(selected.filter((s) => s !== id));
    } else if (selected.length < maxSelect) {
      setSelected([...selected, id]);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[60] flex items-center justify-center p-6 animate-fade-in"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-indigo-50">
          <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
            <span className="text-xl">🎯</span>
            选择归因维度
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            最多选 {maxSelect} 个维度，将对销量缺口进行多维拆解
            {selected.length > 0 && (
              <span className="ml-2 text-purple-600 font-medium">
                已选 {selected.length}/{maxSelect}
              </span>
            )}
          </p>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-2 max-h-[60vh] overflow-y-auto">
          {DIMENSION_OPTIONS.map((dim) => {
            const isSelected = selected.includes(dim.id);
            const disabled = !isSelected && selected.length >= maxSelect;
            return (
              <label
                key={dim.id}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all
                  ${isSelected
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
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex gap-3">
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
            className="flex-1 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 font-medium"
          >
            {loading ? "启动 SOP..." : `开始分析（${selected.length} 个维度）`}
          </button>
        </div>
      </div>
    </div>
  );
}
