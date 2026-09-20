"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  X, Loader2, Layers, Play, BarChart3, Star, Lock, FileText,
} from "lucide-react";
import {
  listTemplates, v2RunTemplate,
  Template, TemplateListResponse,
} from "@/lib/templates-api";

const METRIC_LABEL: Record<string, string> = {
  delivered_units: "总交付量",
  gross_revenue: "总营收",
  customer_leads: "进店线索量",
  conversion_rate: "客流转化率",
  avg_price: "单车成交均价",
};

const DIM_LABELS: Record<string, string> = {
  brand_name: "品牌", region_name: "区域", model_name: "车型",
  energy_type: "能源", price_segment: "价位", monthly: "时间",
};

interface Props {
  onClose: () => void;
  onRun?: (templateId: string) => void;
}

export default function SopTemplateModal({ onClose, onRun }: Props) {
  const router = useRouter();
  const [data, setData] = useState<TemplateListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTemplates()
      .then(setData)
      .catch(() => setError("加载失败"))
      .finally(() => setLoading(false));
  }, []);

  const handleRun = async (tpl: Template) => {
    setRunning(tpl.id);
    try {
      await v2RunTemplate(tpl.id, {});
      onRun?.(tpl.id);
      onClose();
      router.push(`/templates/run/${tpl.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(null);
    }
  };

  const handlePreview = (tpl: Template) => {
    onClose();
    router.push(`/templates/editor/${tpl.id}`);
  };

  // 角色默认模板
  const roleDefault = data
    ? data.system_presets.find((t) => t.id === data.role_default_id)
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-indigo-50">
          <div>
            <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-purple-600" />
              选择 SOP 归因模板
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              完整 SOP 步骤化报告 · 支持多步下钻、横向对比、策略建议
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-white/60 rounded-lg transition-colors">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-6 mt-4 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
            {error}
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-5 h-5 animate-spin text-purple-600" />
              <span className="ml-2 text-sm text-gray-500">加载模板...</span>
            </div>
          ) : (
            <>
              {/* 角色默认（高亮推荐） */}
              {roleDefault && (
                <div>
                  <div className="text-xs font-semibold text-purple-700 mb-2 flex items-center gap-1">
                    <Star className="w-3.5 h-3.5 text-amber-500" />
                    当前角色推荐模板
                  </div>
                  <TemplateCard
                    tpl={roleDefault}
                    highlight
                    running={running === roleDefault.id}
                    onRun={() => handleRun(roleDefault)}
                    onPreview={() => handlePreview(roleDefault)}
                  />
                </div>
              )}

              {/* 系统预设列表 */}
              {data && data.system_presets.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-600 mb-2 flex items-center gap-1">
                    <Lock className="w-3.5 h-3.5" />
                    系统预设模板（{data.system_presets.length}）
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {data.system_presets.map((t) => (
                      <TemplateCard
                        key={t.id}
                        tpl={t}
                        isDefault={t.id === data.role_default_id}
                        running={running === t.id}
                        onRun={() => handleRun(t)}
                        onPreview={() => handlePreview(t)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* 提示 */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-xs text-blue-700 space-y-1">
                <div className="font-medium">💡 如何自定义模板？</div>
                <div>
                  点击卡片右侧「编排」按钮 → 进入 V2 三栏编辑器 → 添加/调整 SOP 步骤 →
                  保存后立即运行完整报告。
                </div>
                <button
                  onClick={() => { onClose(); router.push("/templates/market"); }}
                  className="text-purple-700 hover:underline mt-1"
                >
                  → 去模板市场克隆一个 →
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-100 bg-gray-50 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-white transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
function TemplateCard({
  tpl, highlight, isDefault, running, onRun, onPreview,
}: {
  tpl: Template;
  highlight?: boolean;
  isDefault?: boolean;
  running: boolean;
  onRun: () => void;
  onPreview: () => void;
}) {
  const stepCount = tpl.steps?.length || 0;
  return (
    <div
      className={`rounded-xl border p-4 transition-all ${
        highlight
          ? "border-amber-300 bg-amber-50 ring-2 ring-amber-100"
          : isDefault
            ? "border-purple-300 bg-purple-50"
            : "border-gray-200 bg-white hover:border-purple-200 hover:shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          <FileText className="w-3.5 h-3.5 text-purple-500 flex-shrink-0" />
          <span className="font-semibold text-sm text-gray-900 truncate">{tpl.name}</span>
          {isDefault && (
            <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded-full flex-shrink-0">
              <Star className="w-2.5 h-2.5 inline" />
            </span>
          )}
        </div>
      </div>

      <p className="text-[11px] text-gray-500 mb-2 line-clamp-2">{tpl.description || "（无描述）"}</p>

      {/* 步骤数 + 指标 */}
      <div className="flex items-center gap-2 mb-2 text-[11px]">
        <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">
          {stepCount} 步
        </span>
        <span className="flex items-center gap-0.5 text-blue-600">
          <BarChart3 className="w-3 h-3" />
          {METRIC_LABEL[tpl.metric_key || ""] || "总交付量"}
        </span>
      </div>

      {/* 步骤类型标签 */}
      {stepCount > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {tpl.steps!.slice(0, 4).map((s) => (
            <span key={s.step_id} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-[10px] rounded">
              {s.title}
            </span>
          ))}
          {stepCount > 4 && (
            <span className="text-[10px] text-gray-400">+{stepCount - 4}</span>
          )}
        </div>
      )}

      {/* 操作 */}
      <div className="flex gap-1.5">
        <button
          onClick={onRun}
          disabled={running}
          className="flex-1 flex items-center justify-center gap-1 py-1.5 bg-purple-600 text-white text-xs rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
        >
          {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
          {running ? "启动中..." : "运行 SOP"}
        </button>
        <button
          onClick={onPreview}
          className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          编排
        </button>
      </div>
    </div>
  );
}
