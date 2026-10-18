"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getTemplate,
  listTemplateVersions,
  createRun,
  listRuns,
  archiveTemplate,
  publishNewVersion,
} from "@/lib/template-center-api";
import type {
  Template,
  TemplateVersion,
  TemplateRun,
  StepSpec,
} from "@/lib/template-center-types";
import {
  RUN_STATUS_LABEL,
  RUN_STATUS_COLOR,
  STEP_TYPE_LABEL,
} from "@/lib/template-center-types";
import StepView from "@/components/template-center/StepView";
import { Play, History, ArrowLeft, Trash2, GitBranch, FileEdit } from "lucide-react";

export default function TemplateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [tpl, setTpl] = useState<Template | null>(null);
  const [version, setVersion] = useState<TemplateVersion | null>(null);
  const [runs, setRuns] = useState<TemplateRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useState<Record<string, any>>({});
  const [query, setQuery] = useState("");
  const [running, setRunning] = useState(false);
  const [latestRun, setLatestRun] = useState<{ run: TemplateRun; steps: any[] } | null>(null);
  const [tab, setTab] = useState<"run" | "history">("run");

  useEffect(() => {
    if (!id) return;
    (async () => {
      setLoading(true);
      try {
        const [t, vs, rs] = await Promise.all([
          getTemplate(id),
          listTemplateVersions(id),
          listRuns({ template_id: id, limit: 20 }),
        ]);
        setTpl(t);
        setVersion(vs.items[0] || null);
        setRuns(rs.items);
        // 初始化参数默认值
        if (vs.items[0]) {
          const defaults: Record<string, any> = {};
          for (const step of vs.items[0].steps as StepSpec[]) {
            for (const v of step.variables || []) {
              if (v.default != null) defaults[v.name] = v.default;
            }
          }
          setParams(defaults);
        }
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  async function handleRun() {
    if (!tpl) return;
    setRunning(true);
    setError(null);
    try {
      const r = await createRun(tpl.template_id, {
        user_query: query || `运行模板：${tpl.name}`,
        params,
      });
      setLatestRun(r);
      // 刷新运行列表
      const rs = await listRuns({ template_id: tpl.template_id, limit: 20 });
      setRuns(rs.items);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  async function handleArchive() {
    if (!tpl) return;
    if (!confirm(`确认归档模板「${tpl.name}」？归档后列表默认不显示。`)) return;
    try {
      await archiveTemplate(tpl.template_id);
      router.push("/template-center");
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (loading) {
    return <div className="p-8 text-slate-500">加载中…</div>;
  }
  if (error && !tpl) {
    return (
      <div className="p-8">
        <div className="bg-rose-50 border border-rose-200 rounded p-4 text-rose-700">
          加载失败：{error}
        </div>
        <Link
          href="/template-center"
          className="mt-4 inline-flex items-center gap-2 text-emerald-600 hover:underline"
        >
          <ArrowLeft size={16} /> 返回列表
        </Link>
      </div>
    );
  }
  if (!tpl || !version) return null;

  // 汇总所有变量（按步骤顺序）
  const allVariables: { stepName: string; var: any }[] = [];
  for (const step of version.steps as StepSpec[]) {
    for (const v of step.variables || []) {
      allVariables.push({ stepName: step.name, var: v });
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <Link
            href="/template-center"
            className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-2"
          >
            <ArrowLeft size={14} /> 返回列表
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{tpl.name}</h1>
              <div className="mt-1 flex items-center gap-2 text-sm text-slate-500">
                <span className="font-mono">{tpl.code}</span>
                <span>·</span>
                <span>v{tpl.current_version}</span>
                <span>·</span>
                <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded text-xs">
                  {tpl.category}
                </span>
                {tpl.is_builtin && (
                  <span className="px-2 py-0.5 bg-amber-50 text-amber-700 rounded text-xs">
                    内置
                  </span>
                )}
              </div>
              {tpl.description && (
                <p className="text-sm text-slate-600 mt-2 max-w-3xl">
                  {tpl.description}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Link
                href={`/template-center/${tpl.template_id}/edit`}
                className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 rounded text-sm hover:bg-slate-50"
              >
                <FileEdit size={14} /> 编辑
              </Link>
              {!tpl.is_archived && (
                <button
                  onClick={handleArchive}
                  className="inline-flex items-center gap-1 px-3 py-1.5 border border-rose-300 text-rose-600 rounded text-sm hover:bg-rose-50"
                >
                  <Trash2 size={14} /> 归档
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Body */}
      <div className="max-w-7xl mx-auto px-6 py-5 grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: Steps Overview + Run Form */}
        <div className="lg:col-span-2 space-y-5">
          {/* Steps Overview */}
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
              <GitBranch size={16} /> 执行步骤（共 {(version.steps as StepSpec[]).length} 步）
            </h2>
            <div className="space-y-2">
              {(version.steps as StepSpec[]).map((s, idx) => (
                <div
                  key={idx}
                  className="border-l-4 border-slate-300 pl-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-slate-500">
                      [{idx + 1}]
                    </span>
                    <span className="font-medium text-slate-900">{s.name}</span>
                    <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded">
                      {STEP_TYPE_LABEL[s.type] || s.type}
                    </span>
                  </div>
                  {s.description && (
                    <p className="text-xs text-slate-500 mt-1 ml-7">
                      {s.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Run Result */}
          {latestRun && (
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <h2 className="text-sm font-semibold text-slate-900 mb-3">
                本次执行结果
              </h2>
              <div className="mb-3 flex items-center gap-3">
                <span
                  className={`text-xs px-2 py-1 rounded ${
                    RUN_STATUS_COLOR[latestRun.run.status]
                  }`}
                >
                  {RUN_STATUS_LABEL[latestRun.run.status]}
                </span>
                <span className="text-xs text-slate-500">
                  进度 {latestRun.run.completed_steps}/{latestRun.run.total_steps}
                </span>
                {latestRun.run.duration_ms != null && (
                  <span className="text-xs text-slate-500">
                    ⏱ {latestRun.run.duration_ms}ms
                  </span>
                )}
              </div>
              <StepView steps={latestRun.steps} />
            </div>
          )}

          {/* Tabs: Run / History */}
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
            <div className="flex border-b border-slate-200">
              <button
                onClick={() => setTab("run")}
                className={`px-4 py-2 text-sm font-medium ${
                  tab === "run"
                    ? "text-emerald-600 border-b-2 border-emerald-600"
                    : "text-slate-500 hover:text-slate-700"
                }`}
              >
                <Play size={14} className="inline mr-1" /> 运行
              </button>
              <button
                onClick={() => setTab("history")}
                className={`px-4 py-2 text-sm font-medium ${
                  tab === "history"
                    ? "text-emerald-600 border-b-2 border-emerald-600"
                    : "text-slate-500 hover:text-slate-700"
                }`}
              >
                <History size={14} className="inline mr-1" /> 历史（{runs.length}）
              </button>
            </div>
            <div className="p-5">
              {tab === "run" ? (
                <div className="space-y-3">
                  <div>
                    <label className="text-xs font-medium text-slate-700 block mb-1">
                      用户原始问题
                    </label>
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder={`例如：分析 ${tpl.name}`}
                      className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
                    />
                  </div>
                  {allVariables.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-medium text-slate-700">
                        模板变量
                      </div>
                      {allVariables.map(({ stepName, var: v }) => (
                        <div key={v.name} className="flex items-center gap-2">
                          <label className="text-xs text-slate-600 w-24 truncate">
                            {v.label}
                            {v.required && <span className="text-rose-500">*</span>}
                          </label>
                          <span className="text-xs text-slate-400 font-mono">
                            {stepName.slice(0, 6)}
                          </span>
                          <input
                            type="text"
                            value={params[v.name] || ""}
                            onChange={(e) =>
                              setParams((p) => ({ ...p, [v.name]: e.target.value }))
                            }
                            placeholder={v.default || ""}
                            className="flex-1 px-2 py-1 border border-slate-300 rounded text-sm"
                          />
                        </div>
                      ))}
                    </div>
                  )}
                  {error && (
                    <div className="p-2 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
                      {error}
                    </div>
                  )}
                  <button
                    onClick={handleRun}
                    disabled={running}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700 disabled:opacity-50"
                  >
                    <Play size={16} />
                    {running ? "执行中…" : "运行模板"}
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {runs.length === 0 ? (
                    <div className="text-center text-slate-400 py-6 text-sm">
                      暂无运行记录
                    </div>
                  ) : (
                    runs.map((r) => (
                      <div
                        key={r.run_id}
                        className="flex items-center justify-between p-3 border border-slate-200 rounded"
                      >
                        <div>
                          <div className="text-sm font-medium text-slate-900">
                            {r.user_query}
                          </div>
                          <div className="text-xs text-slate-500 mt-0.5">
                            {new Date(r.created_at).toLocaleString("zh-CN")} · v
                            {r.template_version} · {r.completed_steps}/{r.total_steps} 步
                            {r.duration_ms != null && ` · ${r.duration_ms}ms`}
                          </div>
                        </div>
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            RUN_STATUS_COLOR[r.status]
                          }`}
                        >
                          {RUN_STATUS_LABEL[r.status]}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Sidebar: Version Info */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-900 mb-3">版本信息</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">当前版本</dt>
                <dd className="font-medium">v{version.version}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">状态</dt>
                <dd>
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      version.status === "published"
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-amber-50 text-amber-700"
                    }`}
                  >
                    {version.status === "published" ? "已发布" : "草稿"}
                  </span>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">创建人</dt>
                <dd className="text-slate-700">{version.created_by || "-"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">创建时间</dt>
                <dd className="text-slate-700">
                  {new Date(version.created_at).toLocaleString("zh-CN")}
                </dd>
              </div>
            </dl>
          </div>

          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-900 mb-3">元信息</h2>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-slate-500 text-xs">创建人</dt>
                <dd className="text-slate-700">{tpl.created_by || "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-500 text-xs">创建时间</dt>
                <dd className="text-slate-700">
                  {new Date(tpl.created_at).toLocaleString("zh-CN")}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500 text-xs">更新时间</dt>
                <dd className="text-slate-700">
                  {new Date(tpl.updated_at).toLocaleString("zh-CN")}
                </dd>
              </div>
              {tpl.tags && tpl.tags.length > 0 && (
                <div>
                  <dt className="text-slate-500 text-xs mb-1">标签</dt>
                  <dd className="flex flex-wrap gap-1">
                    {tpl.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded"
                      >
                        #{tag}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
