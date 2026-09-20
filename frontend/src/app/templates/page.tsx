"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Plus, Edit3, Trash2, X, Loader2, FileText, Lock, User, Star, AlertTriangle,
  BarChart3, Store, Play, Layers, ChevronRight,
} from "lucide-react";
import {
  listTemplates, listSupportedMetrics, getTemplate,
  v2CreateTemplate, v2DeleteTemplate, v2RunTemplate,
  STEP_TYPE_META, StepType,
} from "@/lib/templates-api";

interface MetricOption {
  key: string;
  label: string;
  unit: string;
  description: string;
  applicable_dimensions: string[];
}

interface TemplateSummary {
  id: string;
  name: string;
  description: string;
  scope: "system" | "role_default" | "market" | "user";
  owner_role?: string | null;
  owner_user?: string | null;
  dimensions: string[];
  metric_key?: string;
  steps?: { step_type: StepType; title: string; order: number }[];
  created_at?: string;
  updated_at?: string;
}

interface TemplateListResponse {
  system_presets: TemplateSummary[];
  role_default_id: string | null;
  role_defaults_map: Record<string, string>;
  user_templates: TemplateSummary[];
}

const DIMENSION_LABELS: Record<string, string> = {
  brand_name: "品牌",
  region_name: "区域",
  model_name: "车型",
  energy_type: "能源类型",
  price_segment: "价格段",
  monthly: "时间",
};

const ALL_DIMENSIONS = [
  { key: "brand_name",    desc: "广丰 / 广本 / 自主" },
  { key: "region_name",   desc: "华南 / 华北 / 华东 / 华中" },
  { key: "model_name",    desc: "轿车 / SUV / MPV" },
  { key: "energy_type",   desc: "纯电 / 混动 / 燃油" },
  { key: "price_segment", desc: "高价车 / 中价车 / 低价车" },
  { key: "monthly",       desc: "周内波动 / 月初 vs 月末" },
];

const ROLE_LABELS: Record<string, string> = {
  executive: "高管",
  analyst:   "分析师",
  product:   "产品经理",
  visitor:   "访客",
};

const METRIC_LABEL_FALLBACK: Record<string, string> = {
  delivered_units: "总交付量",
  gross_revenue: "总营收",
  customer_leads: "进店线索量",
  conversion_rate: "客流转化率",
  avg_price: "单车成交均价",
};
function getMetricLabel(key?: string): string {
  return METRIC_LABEL_FALLBACK[key || ""] || "总交付量";
}

export default function TemplatesPage() {
  const router = useRouter();
  const [data, setData] = useState<TemplateListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentRole, setCurrentRole] = useState<string>("executive");
  const [currentUser, setCurrentUser] = useState<string>("zhangsan");
  const [metrics, setMetrics] = useState<MetricOption[]>([]);
  const [creating, setCreating] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      // 后端返回的 created_at 可能为 null，使用宽松类型
      const j = await listTemplates(currentRole, currentUser);
      setData(j as unknown as TemplateListResponse);
    } catch (e) {
      console.error("Failed to load templates:", e);
    } finally {
      setLoading(false);
    }
  };

  const loadMetrics = async () => {
    try {
      const m = await listSupportedMetrics();
      setMetrics(m);
    } catch (e) {
      console.warn("Failed to load metrics:", e);
    }
  };

  useEffect(() => {
    loadTemplates();
    loadMetrics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRole, currentUser]);

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除这个模板吗？")) return;
    try {
      await v2DeleteTemplate(id);
      await loadTemplates();
    } catch (e: any) {
      alert(`删除失败: ${e.message}`);
    }
  };

  const handleQuickRun = async (id: string) => {
    setRunning(id);
    setRunError(null);
    try {
      await v2RunTemplate(id, {});
      // 跳到报告页
      router.push(`/templates/run/${id}`);
    } catch (e: any) {
      setRunError(e.message);
    } finally {
      setRunning(null);
    }
  };

  const legacyTemplateCount =
    data?.user_templates.filter((t) => !t.metric_key || t.metric_key === "").length || 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <FileText className="w-8 h-8 text-purple-600" />
              归因维度模板中心
            </h1>
            <p className="text-sm text-gray-500 mt-2">
              SOP 步骤化编排 · 系统预设 / 角色默认 / 我的模板 · 三类模板统一管理
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => router.push("/templates/market")}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-50 text-blue-700 text-sm rounded-lg hover:bg-blue-100 transition-colors border border-blue-200"
            >
              <Store className="w-4 h-4" />
              模板市场
            </button>
            <button
              onClick={() => setCreating(true)}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              新建我的模板
            </button>
          </div>
        </div>

        {/* 角色切换器 */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex items-center gap-4">
          <span className="text-sm text-gray-500">当前角色：</span>
          <div className="flex gap-2">
            {Object.entries(ROLE_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setCurrentRole(key)}
                className={`px-4 py-1.5 text-sm rounded-lg transition-colors ${
                  currentRole === key
                    ? "bg-purple-600 text-white shadow-sm"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          <span className="text-xs text-gray-400">用户：{currentUser}</span>
        </div>

        {/* 老模板迁移提示 */}
        {legacyTemplateCount > 0 && (
          <div className="bg-amber-50 border-l-4 border-amber-400 rounded-r-xl p-4 mb-6 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-sm">
              <div className="font-medium text-amber-900">
                检测到 {legacyTemplateCount} 个旧模板未指定归因指标
              </div>
              <div className="text-xs text-amber-700 mt-1">
                系统已默认按"总交付量"运行。建议点击 ✏️ 进入 V2 编排器补全步骤化 SOP。
              </div>
            </div>
          </div>
        )}

        {/* 运行错误 */}
        {runError && (
          <div className="bg-red-50 border-l-4 border-red-400 rounded-r-xl p-4 mb-6 text-sm text-red-800">
            <strong>运行失败：</strong>{runError}
            <button onClick={() => setRunError(null)} className="ml-3 text-red-600 hover:underline">×</button>
          </div>
        )}

        {/* 角色默认提示 */}
        {data && data.role_default_id && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 flex items-center gap-3">
            <Star className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <div className="text-sm">
              <span className="font-medium text-amber-900">
                {ROLE_LABELS[currentRole]}角色默认模板：
              </span>
              {data.system_presets.find((t) => t.id === data.role_default_id)?.name ||
                data.role_default_id}
              <span className="ml-3 text-xs text-amber-700">
                点击 ▶ 运行可发起完整 SOP 归因
              </span>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
            <span className="ml-2 text-sm text-gray-500">加载模板...</span>
          </div>
        ) : (
          <>
            {/* 系统预设 */}
            <section className="mb-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Lock className="w-4 h-4 text-gray-400" />
                系统预设模板（{data?.system_presets.length || 0}）
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data?.system_presets.map((t) => (
                  <TemplateCard
                    key={t.id}
                    template={t}
                    isDefault={t.id === data.role_default_id}
                    isRunning={running === t.id}
                    onRun={() => handleQuickRun(t.id)}
                    onEdit={() => router.push(`/templates/editor/${t.id}`)}
                    onDelete={() => handleDelete(t.id)}
                  />
                ))}
              </div>
            </section>

            {/* 用户自定义 */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <User className="w-4 h-4 text-emerald-500" />
                我的模板（{data?.user_templates.length || 0}）
              </h2>
              {data?.user_templates.length === 0 ? (
                <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-10 text-center">
                  <p className="text-sm text-gray-400 mb-3">
                    还没有自定义模板。从模板市场克隆一个，或点击右上角"新建我的模板"开始
                  </p>
                  <div className="flex gap-2 justify-center">
                    <button
                      onClick={() => router.push("/templates/market")}
                      className="text-sm text-blue-600 hover:underline"
                    >
                      去模板市场逛逛 →
                    </button>
                    <span className="text-gray-300">|</span>
                    <button
                      onClick={() => setCreating(true)}
                      className="text-sm text-purple-600 hover:underline"
                    >
                      + 立即创建
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data?.user_templates.map((t) => (
                    <TemplateCard
                      key={t.id}
                      template={t}
                      isDefault={false}
                      isRunning={running === t.id}
                      onRun={() => handleQuickRun(t.id)}
                      onEdit={() => router.push(`/templates/editor/${t.id}`)}
                      onDelete={() => handleDelete(t.id)}
                    />
                  ))}
                </div>
              )}
            </section>
          </>
        )}

        {/* 新建模板弹窗（V2 简化版：先创空白模板，再跳编辑器） */}
        {creating && (
          <NewTemplateModal
            metrics={metrics}
            onClose={() => setCreating(false)}
            onSaved={async (templateId) => {
              setCreating(false);
              await loadTemplates();
              router.push(`/templates/editor/${templateId}`);
            }}
          />
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// 模板卡片
// ────────────────────────────────────────────────────────────
function TemplateCard({
  template, isDefault, isRunning, onRun, onEdit, onDelete,
}: {
  template: TemplateSummary;
  isDefault: boolean;
  isRunning: boolean;
  onRun: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const isSystem = template.scope === "system";
  const stepCount = template.steps?.length || 0;
  return (
    <div
      className={`bg-white rounded-xl border p-5 hover:shadow-md transition-all ${
        isDefault ? "border-amber-300 ring-2 ring-amber-100" : "border-gray-200"
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{template.name}</h3>
          {isDefault && (
            <span className="flex items-center gap-0.5 px-2 py-0.5 bg-amber-100 text-amber-700 text-[10px] rounded-full font-medium">
              <Star className="w-3 h-3" />
              角色默认
            </span>
          )}
        </div>
        <div className="flex gap-1 flex-shrink-0">
          <button
            onClick={onEdit}
            className="p-1.5 hover:bg-gray-100 rounded transition-colors"
            title="V2 编排器"
          >
            <Edit3 className="w-3.5 h-3.5 text-gray-500" />
          </button>
          {!isSystem && (
            <button
              onClick={onDelete}
              className="p-1.5 hover:bg-red-50 rounded transition-colors"
              title="删除"
            >
              <Trash2 className="w-3.5 h-3.5 text-red-500" />
            </button>
          )}
        </div>
      </div>
      <p className="text-xs text-gray-500 mb-3 line-clamp-2 min-h-[2.5rem]">
        {template.description || "（无描述）"}
      </p>

      {/* ⭐ V2 标识：SOP 步骤数 */}
      {stepCount > 0 && (
        <div className="mb-2 flex items-center gap-1.5 px-2 py-1 bg-purple-50 rounded text-xs text-purple-700">
          <Layers className="w-3 h-3" />
          <span className="font-medium">{stepCount} 步 SOP</span>
          <ChevronRight className="w-3 h-3 ml-auto" />
        </div>
      )}

      {/* 归因指标标签 */}
      <div className="mb-2 flex items-center gap-1.5">
        <BarChart3 className="w-3 h-3 text-blue-500 flex-shrink-0" />
        <span className="text-xs font-medium text-blue-700">
          {getMetricLabel(template.metric_key)}
        </span>
      </div>

      {/* 维度标签 */}
      <div className="flex flex-wrap gap-1">
        {template.dimensions.slice(0, 6).map((d) => (
          <span
            key={d}
            className="inline-block px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded"
          >
            {DIMENSION_LABELS[d] || d}
          </span>
        ))}
      </div>

      {/* 操作区 */}
      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
        <button
          onClick={onRun}
          disabled={isRunning}
          className="flex items-center gap-1 px-3 py-1 bg-emerald-600 text-white text-xs rounded hover:bg-emerald-700 disabled:opacity-50 transition-colors"
        >
          {isRunning ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Play className="w-3 h-3" />
          )}
          {isRunning ? "执行中..." : "运行 SOP"}
        </button>
        <span className="text-[10px] text-gray-400">
          {isSystem ? "🔒 系统预设" : "✏️ 用户自定义"}
        </span>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// 新建模板弹窗（先用默认 step 创建一个空白模板，再跳编辑器补全）
// ────────────────────────────────────────────────────────────
function NewTemplateModal({
  metrics, onClose, onSaved,
}: {
  metrics: MetricOption[];
  onClose: () => void;
  onSaved: (templateId: string) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [metricKey, setMetricKey] = useState("delivered_units");
  const [dimensions, setDimensions] = useState<string[]>(["brand_name", "region_name"]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentMetricCfg = metrics.find((m) => m.key === metricKey);
  const allowedDims = new Set(
    currentMetricCfg?.applicable_dimensions || ALL_DIMENSIONS.map((d) => d.key)
  );

  const toggle = (key: string) => {
    if (dimensions.includes(key)) {
      setDimensions(dimensions.filter((d) => d !== key));
    } else if (dimensions.length < 4) {
      setDimensions([...dimensions, key]);
    }
  };

  const handleMetricChange = (newKey: string) => {
    setMetricKey(newKey);
    const cfg = metrics.find((m) => m.key === newKey);
    const allowed = new Set(
      cfg?.applicable_dimensions || ALL_DIMENSIONS.map((d) => d.key)
    );
    setDimensions(dimensions.filter((d) => allowed.has(d)));
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError("请输入模板名称");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      // 构造一个最简单的 1 步 SOP（horizontal_compare）
      const result = await v2CreateTemplate({
        name,
        description,
        steps: [
          {
            step_id: `step_init`,
            title: "横向分析",
            step_type: "horizontal_compare",
            metric_key: metricKey,
            group_by: dimensions,
            compare_mode: "plan",
            order: 1,
          },
        ],
        change_reason: "init via modal",
      });
      await onSaved(result.template.id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-purple-50 to-indigo-50">
          <h3 className="text-base font-semibold text-gray-900">新建模板（V2 步骤化）</h3>
          <button onClick={onClose} className="p-1 hover:bg-white/60 rounded">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border-l-4 border-red-400 p-3 text-sm text-red-700 rounded">
              {error}
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-gray-700 mb-1 block">
              模板名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={50}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500"
              placeholder="例如：我的新能源专项复盘"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 mb-1 block">描述（可选）</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={200}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500"
              placeholder="这个模板的适用场景"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 mb-1 flex items-center gap-1">
              <BarChart3 className="w-3.5 h-3.5 text-blue-500" />
              归因指标 <span className="text-red-500">*</span>
            </label>
            <select
              value={metricKey}
              onChange={(e) => handleMetricChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-blue-500 bg-white"
            >
              {metrics.length === 0 ? (
                <option value="delivered_units">总交付量（默认）</option>
              ) : (
                metrics.map((m) => (
                  <option key={m.key} value={m.key}>
                    {m.label}（{m.unit}）
                  </option>
                ))
              )}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 mb-2 block">
              初始维度 <span className="text-gray-400">（最多 4 个，已选 {dimensions.length}/4）</span>
            </label>
            <div className="space-y-1.5">
              {ALL_DIMENSIONS.map((dim) => {
                const checked = dimensions.includes(dim.key);
                const dimAllowed = allowedDims.has(dim.key);
                const disabledByCount = !checked && dimensions.length >= 4;
                const disabled = !dimAllowed || disabledByCount;
                return (
                  <label
                    key={dim.key}
                    className={`flex items-center gap-3 p-2 rounded-lg border transition-all ${
                      !dimAllowed
                        ? "opacity-40 cursor-not-allowed border-gray-100 bg-gray-50"
                        : checked
                          ? "border-purple-300 bg-purple-50 cursor-pointer"
                          : disabledByCount
                            ? "opacity-50 cursor-not-allowed border-gray-100"
                            : "border-gray-200 hover:bg-gray-50 cursor-pointer"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => toggle(dim.key)}
                      className="w-4 h-4 text-purple-600"
                    />
                    <span className="text-sm font-medium text-gray-900">
                      {DIMENSION_LABELS[dim.key]}
                    </span>
                    {!dimAllowed && (
                      <span className="ml-auto text-[10px] text-gray-400">不适用</span>
                    )}
                  </label>
                );
              })}
            </div>
            <p className="text-[10px] text-gray-400 mt-2">
              💡 创建后可进入 V2 编排器修改步骤（添加下钻/横向对比/策略建议等）
            </p>
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex gap-3">
          <button
            onClick={onClose}
            disabled={saving}
            className="flex-1 py-2 text-sm border border-gray-300 rounded-lg hover:bg-white disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim() || dimensions.length === 0}
            className="flex-1 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-1"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {saving ? "创建中..." : "创建并进入编排器"}
          </button>
        </div>
      </div>
    </div>
  );
}
