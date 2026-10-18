"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listTemplates, type ListTemplatesParams } from "@/lib/template-center-api";
import type { Template, TemplateCategory } from "@/lib/template-center-types";
import { Plus, Search, Archive, Code, FileText } from "lucide-react";

const CATEGORIES: { value: TemplateCategory | ""; label: string }[] = [
  { value: "", label: "全部分类" },
  { value: "销售归因", label: "销售归因" },
  { value: "市场归因", label: "市场归因" },
  { value: "库存归因", label: "库存归因" },
  { value: "渠道归因", label: "渠道归因" },
  { value: "自定义", label: "自定义" },
];

export default function TemplateCenterPage() {
  const [items, setItems] = useState<Template[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useState<ListTemplatesParams>({
    limit: 50,
    offset: 0,
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await listTemplates(params);
      setItems(r.items);
      setTotal(r.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.category, params.keyword, params.include_archived]);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">归因模板中心</h1>
            <p className="text-sm text-slate-500 mt-1">
              管理归因分析模板，编排 NL2SQL / 策略 / 聚合 / 结论 的多步执行
            </p>
          </div>
          <Link
            href="/template-center/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition"
          >
            <Plus size={18} /> 新建模板
          </Link>
        </div>
      </header>

      {/* Filter Bar */}
      <div className="max-w-7xl mx-auto px-6 py-5">
        <div className="bg-white rounded-lg border border-slate-200 p-4 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              type="text"
              placeholder="搜索名称 / 编码 / 描述"
              value={params.keyword || ""}
              onChange={(e) =>
                setParams((p) => ({ ...p, keyword: e.target.value || undefined }))
              }
              className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <select
            value={params.category || ""}
            onChange={(e) =>
              setParams((p) => ({
                ...p,
                category: e.target.value || undefined,
              }))
            }
            className="px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <label className="inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={params.include_archived || false}
              onChange={(e) =>
                setParams((p) => ({ ...p, include_archived: e.target.checked }))
              }
              className="rounded"
            />
            <Archive size={14} /> 显示已归档
          </label>
          <div className="text-sm text-slate-500 ml-auto">
            共 <span className="font-semibold text-slate-900">{total}</span> 个模板
          </div>
        </div>

        {/* List */}
        {error && (
          <div className="mt-4 p-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
            加载失败：{error}
          </div>
        )}

        {loading ? (
          <div className="mt-8 text-center text-slate-500">加载中…</div>
        ) : items.length === 0 ? (
          <div className="mt-8 text-center text-slate-400 py-12 bg-white rounded-lg border border-dashed border-slate-300">
            <FileText size={36} className="mx-auto mb-2 opacity-50" />
            没有匹配的模板
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((t) => (
              <Link
                key={t.template_id}
                href={`/template-center/${t.template_id}`}
                className={`block bg-white rounded-lg border ${
                  t.is_archived
                    ? "border-slate-200 opacity-60"
                    : "border-slate-200 hover:border-emerald-400 hover:shadow-md"
                } p-5 transition`}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-slate-900 line-clamp-1">
                    {t.name}
                  </h3>
                  <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded">
                    v{t.current_version}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
                  <Code size={12} />
                  <span className="font-mono">{t.code}</span>
                </div>
                <p className="text-sm text-slate-600 line-clamp-2 mb-3 min-h-[2.5em]">
                  {t.description || "（无描述）"}
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-xs px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded">
                    {t.category}
                  </span>
                  {t.is_builtin && (
                    <span className="text-xs px-2 py-0.5 bg-amber-50 text-amber-700 rounded">
                      内置
                    </span>
                  )}
                  {t.is_archived && (
                    <span className="text-xs px-2 py-0.5 bg-slate-200 text-slate-600 rounded">
                      已归档
                    </span>
                  )}
                </div>
                {t.tags && t.tags.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {t.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
