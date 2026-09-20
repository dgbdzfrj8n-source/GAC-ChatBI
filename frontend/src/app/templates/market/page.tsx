"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Store, Loader2, Copy, ChevronLeft, FileText, BarChart3,
  Star, Lock, User as UserIcon,
} from "lucide-react";
import {
  listTemplates, v2CloneTemplate, STEP_TYPE_META, Template,
} from "@/lib/templates-api";

const DIMENSION_LABELS: Record<string, string> = {
  brand_name: "品牌",
  region_name: "区域",
  model_name: "车型",
  energy_type: "能源类型",
  price_segment: "价格段",
  monthly: "时间",
};

const METRIC_LABEL_FALLBACK: Record<string, string> = {
  delivered_units: "总交付量",
  gross_revenue: "总营收",
  customer_leads: "进店线索量",
  conversion_rate: "客流转化率",
  avg_price: "单车成交均价",
};

export default function TemplateMarketPage() {
  const router = useRouter();
  const [data, setData] = useState<{ system_presets: Template[]; user_templates: Template[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [cloning, setCloning] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      // 取所有模板：系统预设作为"市场"展示源
      const j = await listTemplates();
      setData({
        system_presets: j.system_presets,
        user_templates: j.user_templates,
      });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleClone = async (srcId: string, srcName: string) => {
    if (!confirm(`将「${srcName}」克隆到我的模板？`)) return;
    setCloning(srcId);
    try {
      const newName = prompt("新模板名称（留空用默认「原名（克隆）」）", "");
      const r = await v2CloneTemplate({
        source_template_id: srcId,
        target_scope: "user",
        new_name: newName || undefined,
      });
      alert(`克隆成功！\n新模板 ID：${r.template.id}`);
      router.push(`/templates/editor/${r.template.id}`);
    } catch (e: any) {
      alert(`克隆失败: ${e.message}`);
    } finally {
      setCloning(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-end justify-between">
          <div>
            <button
              onClick={() => router.push("/templates")}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-2"
            >
              <ChevronLeft className="w-4 h-4" />
              返回模板中心
            </button>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Store className="w-8 h-8 text-blue-600" />
              模板市场
            </h1>
            <p className="text-sm text-gray-500 mt-2">
              从系统预设挑选适合的 SOP 一键克隆到我的模板 · 业务用户可在编辑器中个性化修改
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            <span className="ml-2 text-sm text-gray-500">加载市场...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data?.system_presets.map((t) => {
              const isCloning = cloning === t.id;
              return (
                <div
                  key={t.id}
                  className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <FileText className="w-4 h-4 text-purple-500 flex-shrink-0" />
                      <h3 className="font-semibold text-gray-900 truncate">{t.name}</h3>
                    </div>
                    <Lock className="w-3.5 h-3.5 text-gray-400" />
                  </div>

                  <p className="text-xs text-gray-500 mb-3 line-clamp-3 min-h-[3.5rem]">
                    {t.description || "（无描述）"}
                  </p>

                  {/* SOP 步骤概览 */}
                  <div className="mb-3 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-3">
                    <div className="text-[10px] text-purple-700 font-semibold mb-1.5">
                      步骤化 SOP（{t.steps?.length || 0} 步）
                    </div>
                    <div className="space-y-1">
                      {t.steps?.map((s) => {
                        const meta = STEP_TYPE_META[s.step_type];
                        return (
                          <div key={s.step_id} className="flex items-center gap-1.5 text-[11px]">
                            <span className="w-4 h-4 rounded-full bg-purple-100 text-purple-700 text-[9px] font-bold flex items-center justify-center flex-shrink-0">
                              {s.order}
                            </span>
                            <span className="text-base leading-none">{meta?.icon}</span>
                            <span className="truncate text-gray-700">{s.title}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* 维度标签 */}
                  <div className="mb-3">
                    <div className="text-[10px] text-gray-500 mb-1">聚合维度：</div>
                    <div className="flex flex-wrap gap-1">
                      {t.dimensions.map((d) => (
                        <span
                          key={d}
                          className="inline-block px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded"
                        >
                          {DIMENSION_LABELS[d] || d}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* 归因指标 */}
                  <div className="mb-3 flex items-center gap-1.5 text-xs">
                    <BarChart3 className="w-3 h-3 text-blue-500" />
                    <span className="font-medium text-blue-700">
                      {METRIC_LABEL_FALLBACK[t.metric_key || ""] || "总交付量"}
                    </span>
                  </div>

                  {/* 操作 */}
                  <button
                    onClick={() => handleClone(t.id, t.name)}
                    disabled={isCloning}
                    className="w-full flex items-center justify-center gap-1.5 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {isCloning ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                    {isCloning ? "克隆中..." : "克隆为我的模板"}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* 我的模板（已克隆） */}
        {data && data.user_templates.length > 0 && (
          <div className="mt-10">
            <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <UserIcon className="w-4 h-4 text-emerald-500" />
              我已经克隆的模板（{data.user_templates.length}）
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.user_templates.map((t) => (
                <div
                  key={t.id}
                  className="bg-emerald-50 rounded-xl border border-emerald-200 p-4"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Star className="w-4 h-4 text-emerald-500" />
                    <h3 className="font-semibold text-gray-900 truncate">{t.name}</h3>
                  </div>
                  <p className="text-xs text-gray-600 mb-2 line-clamp-2">
                    {t.description || "（无描述）"}
                  </p>
                  <button
                    onClick={() => router.push(`/templates/editor/${t.id}`)}
                    className="text-xs text-emerald-700 hover:underline"
                  >
                    前往编辑器修改 →
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
