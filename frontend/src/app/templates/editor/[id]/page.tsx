"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  Layers, Plus, Trash2, ArrowUp, ArrowDown, Save, Loader2, Play, ChevronLeft,
  AlertCircle, Eye, FileText, History, X, Check,
} from "lucide-react";
import {
  getTemplate, v2UpdateTemplate, v2PreviewTemplate, v2RunTemplate,
  v2GetAudit, v2CloneTemplate, adminUpdateTemplate,
  STEP_TYPE_META, StepType, StepSpec, Template,
} from "@/lib/templates-api";
import { getUser } from "@/lib/auth";

const DIMENSION_LABELS: Record<string, string> = {
  brand_name: "品牌",
  region_name: "区域",
  model_name: "车型",
  energy_type: "能源类型",
  price_segment: "价格段",
  monthly: "时间",
};

const ALL_DIMENSIONS = [
  "brand_name", "region_name", "model_name", "energy_type", "price_segment", "monthly",
];

const STATUS_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  ok:   { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  warn: { bg: "bg-amber-50",   text: "text-amber-700",   dot: "bg-amber-500"   },
  bad:  { bg: "bg-red-50",     text: "text-red-700",     dot: "bg-red-500"     },
  info: { bg: "bg-blue-50",    text: "text-blue-700",    dot: "bg-blue-500"    },
};

export default function TemplateEditorPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const templateId = params?.id || "";

  const [tpl, setTpl] = useState<Template | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewResult, setPreviewResult] = useState<any | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditHistory, setAuditHistory] = useState<any[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);
  // [Bug1 修复] 用 React state 替代 window.__selStep 反模式
  // - 进入编辑器默认选中 steps[0]（让中栏不再是空白占位文）
  // - 选中状态用 setState 触发重渲染，与 tpl 保持一致
  const [selectedStepIdx, setSelectedStepIdx] = useState<number | null>(null);

  // 加载模板 + 当前用户
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const t = await getTemplate(templateId);
        if (!t) {
          setError("模板不存在");
          return;
        }
        setTpl(t);
        // [Bug1 修复] 默认选中第一个 step，避免中栏空白
        if (t.steps && t.steps.length > 0) {
          setSelectedStepIdx(0);
        }
        const u = getUser();
        setCurrentUser(u);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [templateId]);

  // [Bug1 修复] triggerPreview 必须先定义，下面的 useEffect 依赖它
  const triggerPreview = useCallback(async (cur: Template) => {
    if (!cur) return;
    setPreviewLoading(true);
    setPreviewResult(null);
    try {
      const r = await v2PreviewTemplate(cur.id, {});
      setPreviewResult(r);
    } catch (e: any) {
      setPreviewResult({ error: e.message });
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  // [Bug1 修复] 进入编辑器就自动跑一次预览（不再等 dirty 触发）
  // - 原因：之前 `if (!dirty) return` 导致首次进入右栏永远是空白
  // - 加一个 initialPreviewRanRef 防止依赖 tpl 变化时反复触发
  const initialPreviewRanRef = useRef<string | null>(null);
  useEffect(() => {
    if (!tpl) return;
    if (initialPreviewRanRef.current === tpl.id) return;
    initialPreviewRanRef.current = tpl.id;
    triggerPreview(tpl);
  }, [tpl, triggerPreview]);

  // 编辑时自动预览（debounce，dirty=true 才触发）
  useEffect(() => {
    if (!tpl || !dirty) return;
    const handle = setTimeout(() => triggerPreview(tpl), 600);
    return () => clearTimeout(handle);
  }, [tpl, dirty, triggerPreview]);

  const updateStep = (idx: number, patch: Partial<StepSpec>) => {
    if (!tpl) return;
    const newSteps = tpl.steps.map((s, i) => (i === idx ? { ...s, ...patch } : s));
    setTpl({ ...tpl, steps: newSteps });
    setDirty(true);
  };

  const addStep = (type: StepType) => {
    if (!tpl) return;
    const meta = STEP_TYPE_META[type];
    const newStep: StepSpec = {
      step_id: `step_${Date.now().toString(36)}`,
      title: meta.label,
      step_type: type,
      metric_key: tpl.metric_key || "delivered_units",
      group_by: [],
      compare_mode: "plan",
      compare_period: type === "yoy_compare" ? "2025-Q3" : (type === "period_compare" ? "month" : null),
      depends_on: null,
      threshold: type === "overall_kpi" ? { warn: 0.95, bad: 0.85 } : null,
      top_n: type === "drill_down" ? 10 : null,
      order: tpl.steps.length + 1,
    };
    setTpl({ ...tpl, steps: [...tpl.steps, newStep] });
    setDirty(true);
  };

  const removeStep = (idx: number) => {
    if (!tpl) return;
    const newSteps = tpl.steps.filter((_, i) => i !== idx)
      .map((s, i) => ({ ...s, order: i + 1 }));  // 重排
    setTpl({ ...tpl, steps: newSteps });
    setDirty(true);
  };

  const moveStep = (idx: number, dir: -1 | 1) => {
    if (!tpl) return;
    const target = idx + dir;
    if (target < 0 || target >= tpl.steps.length) return;
    const newSteps = [...tpl.steps];
    [newSteps[idx], newSteps[target]] = [newSteps[target], newSteps[idx]];
    newSteps.forEach((s, i) => (s.order = i + 1));
    setTpl({ ...tpl, steps: newSteps });
    setDirty(true);
  };

  const handleSave = async (opts?: { silent?: boolean }) => {
    // [兼容] 按钮 onClick={handleSave} 会把 MouseEvent 作为 opts 传进来
    // - MouseEvent 没有 .silent 字段，所以这种调用会走"非静默"分支（弹 alert）
    // - 只有 handleRun 显式传 { silent: true } 才会走静默分支
    if (opts && typeof (opts as any).preventDefault === "function") {
      opts = undefined;
    }
    if (!tpl) return;
    setSaving(true);
    try {
      // admin 可改 preset_*；业务用户只能改自己的 user scope
      const isAdmin = currentUser?.role === "admin" || currentUser?.role === "analyst";
      const isPreset = tpl.id.startsWith("preset_");
      const isSystemScope = tpl.scope === "system" || tpl.scope === "market";
      const needAdmin = isPreset || isSystemScope;

      // [Bug2 修复] 业务用户尝试编辑 system preset / role_default 时给出明确提示
      // - 之前直接 alert `保存失败: 权限不足` 让用户摸不着头脑
      // - 现在的策略：
      //   1) 业务用户编辑 system preset：提示"无法直接修改，请先克隆到我的模板"（不做静默 403）
      //   2) 业务用户编辑 market 模板：同上，提示克隆
      //   3) admin/analyst：照常走 admin 端点
      //   4) silent=true（运行前自动保存）：不弹 confirm，直接抛错
      if (needAdmin && !isAdmin) {
        if (opts?.silent) {
          // 静默模式：业务用户不能直接保存 system preset，抛错让上层处理
          throw new Error("业务用户无法直接修改系统预设，请先克隆到我的模板");
        }
        const confirmClone = window.confirm(
          `当前模板是「${isPreset ? "系统预设" : "市场模板"}」，业务用户无法直接修改。\n\n` +
          `点击"确定"将自动克隆一份到"我的模板"并跳转到新模板继续编辑。`
        );
        if (confirmClone) {
          // 调用 clone API（会自动跳到新模板的编辑器）
          const cloned = await v2CloneTemplate({
            source_template_id: tpl.id,
            target_scope: "user",
            new_name: `${tpl.name} (我的副本)`,
          });
          // 跳到克隆后的新模板编辑器
          router.push(`/templates/editor/${cloned.template.id}`);
          return;
        }
        // 用户取消，不保存
        return;
      }

      // 走到这里说明是合法的保存请求
      const fn = needAdmin ? adminUpdateTemplate : v2UpdateTemplate;
      await fn(tpl.id, {
        name: tpl.name,
        description: tpl.description,
        steps: tpl.steps,
        change_reason: "edit via editor",
      });
      setDirty(false);
    } catch (e: any) {
      alert(`保存失败: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    if (!tpl) return;
    try {
      // [Bug5 修复] dirty=true 时先静默保存当前编辑内容
      // - 原因：v2RunTemplate 跑的是 DB 里的版本，前端 dirty 的 steps 不会生效
      // - dirty=false 时直接跑（没改东西，没必要保存）
      // - 静默保存：不弹 alert 干扰用户，失败则中断运行
      if (dirty) {
        try {
          await handleSave({ silent: true });
        } catch (saveErr: any) {
          // 保存失败（例如无权限）→ 阻止运行，让用户看到保存错误
          throw new Error(`运行前保存失败: ${saveErr.message}`);
        }
      }
      await v2RunTemplate(tpl.id, {});
      router.push(`/templates/run/${tpl.id}`);
    } catch (e: any) {
      alert(`运行失败: ${e.message}`);
    }
  };

  const openAudit = async () => {
    setAuditOpen(true);
    try {
      const j = await v2GetAudit(templateId, 20);
      setAuditHistory(j.history || []);
    } catch (e: any) {
      setAuditHistory([]);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
        <span className="ml-2 text-sm text-gray-500">加载模板...</span>
      </div>
    );
  }
  if (error || !tpl) {
    return (
      <div className="min-h-screen p-8">
        <div className="max-w-2xl mx-auto bg-red-50 border-l-4 border-red-400 p-4 rounded text-sm text-red-800">
          {error || "模板不存在"}
        </div>
        <button
          onClick={() => router.push("/templates")}
          className="mt-4 text-purple-600 hover:underline"
        >
          ← 返回模板列表
        </button>
      </div>
    );
  }

  // [Bug1 修复] selectedStepIdx 已改为 React state（见组件顶部 useState）
  // 原反模式 `const selectedStepIdx = (window as any).__selStep ?? null` 已被移除
  const activeStep = selectedStepIdx !== null ? tpl.steps[selectedStepIdx] : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-purple-50">
      {/* 顶部 */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
          <button
            onClick={() => router.push("/templates")}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
          >
            <ChevronLeft className="w-4 h-4" />
            返回
          </button>
          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={tpl.name}
              onChange={(e) => { setTpl({ ...tpl, name: e.target.value }); setDirty(true); }}
              className="text-lg font-semibold text-gray-900 bg-transparent border-none focus:outline-none w-full"
            />
            <input
              type="text"
              value={tpl.description}
              onChange={(e) => { setTpl({ ...tpl, description: e.target.value }); setDirty(true); }}
              placeholder="模板描述"
              className="text-xs text-gray-500 bg-transparent border-none focus:outline-none w-full"
            />
          </div>
          {dirty && (
            <span className="text-xs text-amber-600 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              未保存
            </span>
          )}
          <button
            onClick={openAudit}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded"
          >
            <History className="w-4 h-4" />
            历史
          </button>
          <button
            onClick={() => handleSave()}
            disabled={saving || !dirty}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
            保存
          </button>
          <button
            onClick={handleRun}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-emerald-600 text-white rounded hover:bg-emerald-700"
          >
            <Play className="w-3 h-3" />
            运行 SOP
          </button>
        </div>
      </header>

      {/* 三栏布局 */}
      <div className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-12 gap-6">
        {/* 左：步骤列表 */}
        <div className="col-span-3">
          <div className="bg-white rounded-xl border border-gray-200 p-4 sticky top-20">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-500" />
              SOP 步骤 ({tpl.steps.length})
            </h3>
            <div className="space-y-1.5">
              {tpl.steps.map((s, i) => {
                const meta = STEP_TYPE_META[s.step_type];
                return (
                  <div
                    key={s.step_id}
                    onClick={() => setSelectedStepIdx(i)}
                    className={`group flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-all hover:bg-purple-50 ${
                      selectedStepIdx === i ? "border-purple-300 bg-purple-50" : "border-gray-200"
                    }`}
                  >
                    <span className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 text-xs font-bold flex items-center justify-center flex-shrink-0">
                      {s.order}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-gray-900 truncate">{s.title}</div>
                      <div className="text-[10px] text-gray-500">{meta?.icon} {meta?.label || s.step_type}</div>
                    </div>
                    <div className="opacity-0 group-hover:opacity-100 flex gap-0.5">
                      <button
                        onClick={(e) => { e.stopPropagation(); moveStep(i, -1); }}
                        disabled={i === 0}
                        className="p-0.5 hover:bg-gray-200 rounded disabled:opacity-30"
                      >
                        <ArrowUp className="w-3 h-3 text-gray-500" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); moveStep(i, 1); }}
                        disabled={i === tpl.steps.length - 1}
                        className="p-0.5 hover:bg-gray-200 rounded disabled:opacity-30"
                      >
                        <ArrowDown className="w-3 h-3 text-gray-500" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); removeStep(i); }}
                        className="p-0.5 hover:bg-red-100 rounded"
                      >
                        <Trash2 className="w-3 h-3 text-red-500" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 添加步骤 */}
            <div className="mt-3 pt-3 border-t border-gray-100">
              <div className="text-[10px] text-gray-500 mb-2">添加步骤：</div>
              <div className="grid grid-cols-2 gap-1">
                {Object.entries(STEP_TYPE_META).map(([type, meta]) => (
                  <button
                    key={type}
                    onClick={() => addStep(type as StepType)}
                    className="flex items-center gap-1 p-1.5 text-[10px] bg-gray-50 hover:bg-purple-50 border border-gray-200 rounded text-gray-700"
                  >
                    <span>{meta.icon}</span>
                    <span className="truncate">{meta.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 中：步骤编辑表单 */}
        <div className="col-span-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5 sticky top-20">
            {activeStep ? (
              <StepForm
                step={activeStep}
                stepIndex={selectedStepIdx!}
                allSteps={tpl.steps}
                onChange={(patch) => updateStep(selectedStepIdx!, patch)}
              />
            ) : (
              <div className="text-center py-10 text-sm text-gray-400">
                <Layers className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                点击左侧任一步骤开始编辑<br/>
                或从底部"添加步骤"新增
              </div>
            )}
          </div>
        </div>

        {/* 右：实时预览 */}
        <div className="col-span-5">
          <div className="bg-white rounded-xl border border-gray-200 p-5 sticky top-20 max-h-[calc(100vh-100px)] overflow-y-auto">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Eye className="w-4 h-4 text-emerald-500" />
              实时预览（前 2 步）
              {previewLoading && <Loader2 className="w-3 h-3 animate-spin text-gray-400 ml-auto" />}
            </h3>
            {previewResult?.error ? (
              <div className="bg-red-50 border-l-4 border-red-400 p-3 rounded text-xs text-red-700">
                {previewResult.error}
              </div>
            ) : previewResult ? (
              <div className="space-y-3">
                {previewResult.report?.map((s: any) => {
                  const style = STATUS_STYLES[s.status] || STATUS_STYLES.info;
                  return (
                    <div key={s.step_id} className={`rounded-lg border border-gray-200 p-3 ${style.bg}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`w-2 h-2 rounded-full ${style.dot}`} />
                        <span className={`text-xs font-semibold ${style.text}`}>
                          [{s.status.toUpperCase()}]
                        </span>
                        <span className="text-xs font-medium text-gray-900">{s.title}</span>
                        <span className="text-[10px] text-gray-400 ml-auto">{s.execution_time_ms}ms</span>
                      </div>
                      <p className="text-xs text-gray-700 leading-relaxed mb-2">{s.conclusion}</p>
                      {s.data && s.data.length > 0 && (
                        <div className="bg-white rounded border border-gray-100 overflow-x-auto">
                          <table className="w-full text-[10px]">
                            <thead>
                              <tr className="bg-gray-50">
                                {(s.columns || Object.keys(s.data[0])).map((c: string) => (
                                  <th key={c} className="px-2 py-1 text-left text-gray-500 font-medium">
                                    {c}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {s.data.slice(0, 5).map((row: any, ri: number) => (
                                <tr key={ri} className="border-t border-gray-100">
                                  {(s.columns || Object.keys(row)).map((c: string) => (
                                    <td key={c} className="px-2 py-1 text-gray-700">
                                      {typeof row[c] === "number" ? row[c].toFixed(2) : String(row[c])}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {s.data.length > 5 && (
                            <div className="text-[10px] text-gray-400 text-center py-1">
                              还有 {s.data.length - 5} 行...
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
                {previewResult.executive_summary && (
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                    <div className="text-[10px] text-purple-700 font-semibold mb-1">高管摘要</div>
                    <div className="text-xs text-purple-900">{previewResult.executive_summary}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-10 text-sm text-gray-400">
                {dirty ? "编辑后将自动预览..." : "修改模板后此处显示 DuckDB 查询结果"}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 审计历史抽屉 */}
      {auditOpen && (
        <AuditDrawer
          history={auditHistory}
          onClose={() => setAuditOpen(false)}
        />
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// 单步骤编辑表单
// ────────────────────────────────────────────────────────────
function StepForm({
  step, stepIndex, allSteps, onChange,
}: {
  step: StepSpec;
  stepIndex: number;
  allSteps: StepSpec[];
  onChange: (patch: Partial<StepSpec>) => void;
}) {
  const meta = STEP_TYPE_META[step.step_type];
  const availableUpstream = allSteps
    .slice(0, stepIndex)
    .filter((s) => s.step_type !== "strategy_recommend")
    .map((s) => ({ id: s.step_id, title: s.title }));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
        <span className="text-xl">{meta?.icon}</span>
        <span className="text-sm font-semibold text-gray-900">{meta?.label}</span>
        <span className="text-xs text-gray-400">order = {step.order}</span>
      </div>

      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">步骤标题</label>
        <input
          type="text"
          value={step.title}
          onChange={(e) => onChange({ title: e.target.value })}
          maxLength={30}
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-purple-500"
        />
      </div>

      <div>
        <label className="text-xs font-medium text-gray-700 mb-1 block">归因指标</label>
        <select
          value={step.metric_key}
          onChange={(e) => onChange({ metric_key: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm bg-white"
        >
          <option value="delivered_units">总交付量（辆）</option>
          <option value="gross_revenue">总营收（元）</option>
          <option value="customer_leads">进店线索量（条）</option>
          <option value="conversion_rate">客流转化率（%）</option>
          <option value="avg_price">单车成交均价（元/辆）</option>
        </select>
      </div>

      {/* group_by：除 overall_kpi/yoy/period/strategy 外都需要 */}
      {!["overall_kpi", "strategy_recommend"].includes(step.step_type) && (
        <div>
          <label className="text-xs font-medium text-gray-700 mb-1 block">聚合维度（多选）</label>
          <div className="flex flex-wrap gap-1">
            {ALL_DIMENSIONS.map((d) => {
              const checked = step.group_by.includes(d);
              return (
                <button
                  key={d}
                  type="button"
                  onClick={() => {
                    const newDims = checked
                      ? step.group_by.filter((x) => x !== d)
                      : [...step.group_by, d];
                    onChange({ group_by: newDims });
                  }}
                  className={`px-2 py-1 text-xs rounded border ${
                    checked
                      ? "bg-purple-600 text-white border-purple-600"
                      : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {DIMENSION_LABELS[d] || d}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* 对比模式 */}
      {["overall_kpi", "yoy_compare", "period_compare"].includes(step.step_type) && (
        <>
          <div>
            <label className="text-xs font-medium text-gray-700 mb-1 block">对比基准</label>
            <select
              value={step.compare_mode}
              onChange={(e) => onChange({ compare_mode: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm bg-white"
            >
              <option value="plan">vs 目标（plan）</option>
              <option value="yoy">vs 同比（yoy）</option>
              <option value="mom">vs 环比（mom）</option>
              <option value="yoy_mom">vs 同比 + 环比</option>
            </select>
          </div>
          {["yoy_compare", "period_compare"].includes(step.step_type) && (
            <div>
              <label className="text-xs font-medium text-gray-700 mb-1 block">对比期</label>
              <input
                type="text"
                value={step.compare_period || ""}
                onChange={(e) => onChange({ compare_period: e.target.value || null })}
                placeholder="如 2025-Q3 / month"
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
              />
            </div>
          )}
        </>
      )}

      {/* 阈值：overall_kpi 可配 */}
      {step.step_type === "overall_kpi" && (
        <div>
          <label className="text-xs font-medium text-gray-700 mb-1 block">达成率阈值</label>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-amber-600">warn (低于)</label>
              <input
                type="number"
                step="0.01"
                min="0" max="2"
                value={step.threshold?.warn ?? 0.95}
                onChange={(e) =>
                  onChange({
                    threshold: { ...(step.threshold || {}), warn: parseFloat(e.target.value) },
                  })
                }
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>
            <div>
              <label className="text-[10px] text-red-600">bad (低于)</label>
              <input
                type="number"
                step="0.01"
                min="0" max="2"
                value={step.threshold?.bad ?? 0.85}
                onChange={(e) =>
                  onChange({
                    threshold: { ...(step.threshold || {}), bad: parseFloat(e.target.value) },
                  })
                }
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>
          </div>
        </div>
      )}

      {/* top_n：drill_down 可配 */}
      {["drill_down", "cross_attribution", "anomaly_alert"].includes(step.step_type) && (
        <div>
          <label className="text-xs font-medium text-gray-700 mb-1 block">Top N（截断）</label>
          <input
            type="number"
            min="1"
            max="100"
            value={step.top_n ?? 10}
            onChange={(e) => onChange({ top_n: parseInt(e.target.value) })}
            className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
          />
        </div>
      )}

      {/* depends_on：strategy_recommend 必填 */}
      {step.step_type === "strategy_recommend" && (
        <div>
          <label className="text-xs font-medium text-gray-700 mb-1 block">
            依赖上游 step <span className="text-red-500">*</span>
          </label>
          {availableUpstream.length === 0 ? (
            <div className="text-xs text-amber-600 bg-amber-50 p-2 rounded">
              ⚠ 策略建议必须在其他 step 之后
            </div>
          ) : (
            <select
              value={step.depends_on || ""}
              onChange={(e) => onChange({ depends_on: e.target.value || null })}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm bg-white"
            >
              <option value="">（选择依赖）</option>
              {availableUpstream.map((u) => (
                <option key={u.id} value={u.id}>{u.title}</option>
              ))}
            </select>
          )}
        </div>
      )}

      <div className="pt-3 border-t border-gray-100 text-[10px] text-gray-400">
        step_id: <code className="bg-gray-100 px-1 rounded">{step.step_id}</code>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// 审计历史抽屉
// ────────────────────────────────────────────────────────────
function AuditDrawer({
  history, onClose,
}: {
  history: any[];
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-40 flex">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-96 bg-white border-l border-gray-200 shadow-xl flex flex-col">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <History className="w-4 h-4 text-purple-500" />
            模板变更历史
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {history.length === 0 ? (
            <div className="text-center text-sm text-gray-400 py-10">暂无变更记录</div>
          ) : (
            history.map((h) => (
              <div key={h.audit_id} className="border border-gray-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded font-medium">
                    v{h.version_no}
                  </span>
                  <span className="text-xs text-gray-600">{h.changed_by || "unknown"}</span>
                </div>
                <div className="text-xs text-gray-700 mb-1">{h.change_reason || "（无原因）"}</div>
                <div className="text-[10px] text-gray-400">{h.changed_at}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
