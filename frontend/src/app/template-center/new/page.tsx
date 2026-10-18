"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createTemplate, getStepTypes, getCategories } from "@/lib/template-center-api";
import type { StepType, StepSpec } from "@/lib/template-center-types";
import { STEP_TYPE_LABEL } from "@/lib/template-center-types";
import { Plus, Trash2, Save, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function NewTemplatePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("自定义");
  const [tags, setTags] = useState("");
  const [steps, setSteps] = useState<Partial<StepSpec>[]>([
    { name: "查询销量", type: "nl2sql", description: "", variables: [] },
  ]);
  const [stepTypes, setStepTypes] = useState<{ value: StepType; label: string; description: string }[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [st, cs] = await Promise.all([getStepTypes(), getCategories()]);
        setStepTypes(st.items);
        setCategories(cs.items.map((c) => c.value));
      } catch (e: any) {
        setError(e.message);
      }
    })();
  }, []);

  function addStep() {
    setSteps((s) => [
      ...s,
      { name: `新步骤 ${s.length + 1}`, type: "nl2sql", description: "", variables: [] },
    ]);
  }

  function removeStep(idx: number) {
    setSteps((s) => s.filter((_, i) => i !== idx));
  }

  function updateStep(idx: number, patch: Partial<StepSpec>) {
    setSteps((s) => s.map((step, i) => (i === idx ? { ...step, ...patch } : step)));
  }

  async function handleSubmit() {
    if (!name || !code) {
      setError("名称和编码必填");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const tpl = await createTemplate({
        name,
        code: code.toLowerCase().replace(/[^a-z0-9_]/g, "_"),
        description,
        category,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
        steps: steps.filter((s) => s.name && s.type),
      });
      router.push(`/template-center/${tpl.template_id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-5 flex items-center justify-between">
          <div>
            <Link
              href="/template-center"
              className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-2"
            >
              <ArrowLeft size={14} /> 返回列表
            </Link>
            <h1 className="text-2xl font-bold text-slate-900">新建归因模板</h1>
          </div>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
          >
            <Save size={16} />
            {submitting ? "保存中…" : "保存"}
          </button>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-5 space-y-5">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded text-sm text-rose-700">
            {error}
          </div>
        )}

        {/* 基本信息 */}
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-900">基本信息</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-600 block mb-1">
                名称 <span className="text-rose-500">*</span>
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="销售环比下降归因"
                className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-600 block mb-1">
                编码 <span className="text-rose-500">*</span>
                <span className="text-slate-400 ml-1">(英文/数字/下划线)</span>
              </label>
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="sales_attr_qoq"
                className="w-full px-3 py-2 border border-slate-300 rounded text-sm font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-slate-600 block mb-1">分类</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded text-sm bg-white"
              >
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-600 block mb-1">
                标签 <span className="text-slate-400">(逗号分隔)</span>
              </label>
              <input
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="销售, 环比, 下滑"
                className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-600 block mb-1">描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="业务说明"
              className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
            />
          </div>
        </div>

        {/* 步骤编辑 */}
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">
              执行步骤 <span className="text-slate-400">({steps.length})</span>
            </h2>
            <button
              onClick={addStep}
              className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 rounded text-sm hover:bg-slate-50"
            >
              <Plus size={14} /> 添加步骤
            </button>
          </div>

          {steps.map((step, idx) => (
            <div
              key={idx}
              className="border border-slate-200 rounded p-4 space-y-3 relative"
            >
              <div className="flex items-center justify-between">
                <div className="text-xs font-mono text-slate-500">[{idx + 1}]</div>
                {steps.length > 1 && (
                  <button
                    onClick={() => removeStep(idx)}
                    className="text-rose-500 hover:text-rose-700"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-600 block mb-1">步骤名</label>
                  <input
                    value={step.name || ""}
                    onChange={(e) => updateStep(idx, { name: e.target.value })}
                    className="w-full px-2 py-1.5 border border-slate-300 rounded text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-600 block mb-1">类型</label>
                  <select
                    value={step.type || "nl2sql"}
                    onChange={(e) => updateStep(idx, { type: e.target.value as StepType })}
                    className="w-full px-2 py-1.5 border border-slate-300 rounded text-sm bg-white"
                  >
                    {stepTypes.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-600 block mb-1">说明</label>
                <input
                  value={step.description || ""}
                  onChange={(e) => updateStep(idx, { description: e.target.value })}
                  className="w-full px-2 py-1.5 border border-slate-300 rounded text-sm"
                />
              </div>
              {step.type === "nl2sql" && (
                <div>
                  <label className="text-xs text-slate-600 block mb-1">
                    NL2SQL 子问题模板
                    <span className="text-slate-400 ml-1">(支持 {`{var}`} 占位)</span>
                  </label>
                  <textarea
                    value={step.question || ""}
                    onChange={(e) => updateStep(idx, { question: e.target.value })}
                    rows={2}
                    placeholder="查询 {brand} {month} 各车型销量"
                    className="w-full px-2 py-1.5 border border-slate-300 rounded text-sm font-mono"
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
