'use client';

import { useEffect, useMemo, useState, useRef } from 'react';
import Link from 'next/link';

const API_URL =
  typeof window !== 'undefined'
    ? localStorage.getItem('apiUrl') || process.env.NEXT_PUBLIC_API_URL || 'https://gac-chatbi-api.onrender.com'
    : process.env.NEXT_PUBLIC_API_URL || 'https://gac-chatbi-api.onrender.com';

// ── 接口定义 ────────────────────────────────────────────────
interface Metric {
  metric_id: string;
  metric_name: string;
  business_domain: string;
  definition: string;
  unit: string;
  calculation_rule: string;
  required_tables?: string[];   // 指标用到了哪些表（从 metrics_dict.json 透传）
  join_condition?: string;       // 表间关联条件
  example_query?: string;
  _last_modified?: string;
  _modified_fields?: string[];
}

interface Dimension {
  table: string;
  field: string;
  type: string;
  description: string;
  synonyms: string[];
  domain: string;
}

interface Term {
  name: string;
  definition: string;
  synonyms: string[];
  related_metrics: string[];
  _last_modified?: string;
  _modified_fields?: string[];
}

interface Snapshot {
  version: string;
  domain_group: string;
  metrics: Metric[];
  dimensions: Dimension[];
  glossary: Term[];
}

type TabKey = 'metrics' | 'dimensions' | 'glossary';

// 指标 ↔ 维度 ↔ 表 三角映射的派生数据结构
interface MetricDimMap {
  // 指标 ID → 该指标涉及哪些表
  metricTables: Record<string, string[]>;
  // 表名 → 该表上有哪些字段
  tableFields: Record<string, string[]>;
  // 指标 ID → 该指标涉及哪些维度字段（field）
  metricFields: Record<string, string[]>;
  // 字段全名 → 被哪些指标引用
  fieldMetrics: Record<string, string[]>;
  // 表名 → 被哪些指标引用
  tableMetrics: Record<string, string[]>;
}

export default function SemanticLayerPage() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [tab, setTab] = useState<TabKey>('metrics');
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Metric | Term | null>(null);
  const [editKind, setEditKind] = useState<'metric' | 'term'>('metric');
  const [toast, setToast] = useState<{ type: 'ok' | 'err'; msg: string } | null>(null);
  // 跨 Tab 导航锚点
  const [navTarget, setNavTarget] = useState<{ type: 'metric'; id: string } | { type: 'table'; name: string } | { type: 'field'; table: string; field: string } | null>(null);
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 预览
  const [previewQ, setPreviewQ] = useState('广汽埃安3月销量达成率');
  const [previewRes, setPreviewRes] = useState<any>(null);
  const [previewing, setPreviewing] = useState(false);

  // ── 计算「指标-维度-表」三角映射关系 ────────────────────────
  const map = useMemo<MetricDimMap>(() => {
    if (!snap) return { metricTables: {}, tableFields: {}, metricFields: {}, fieldMetrics: {}, tableMetrics: {} };

    const metricTables: Record<string, string[]> = {};
    const metricFields: Record<string, string[]> = {};
    const tableFields: Record<string, string[]> = {};
    const fieldMetrics: Record<string, string[]> = {};
    const tableMetrics: Record<string, string[]> = {};

    // 初始化 tableFields（维度层分组）
    for (const d of snap.dimensions) {
      (tableFields[d.table] ??= []).push(d.field);
    }

    // 扫描每个指标的 example_query，把 SELECT / WHERE / GROUP BY / ON 后的字段抽出来
    const FIELD_RE = /\b(brand_name|model_name|region_name|channel_name|sale_date|year_month|expense_date|delivered_units|gross_revenue|discount_rate|customer_leads|target_units|target_revenue|expense_limit|expense_amount|leads_generated)\b/g;
    for (const m of snap.metrics) {
      const tables = m.required_tables ?? [];
      metricTables[m.metric_id] = tables;
      tables.forEach(t => {
        (tableMetrics[t] ??= []).push(m.metric_id);
      });
      const sql = m.example_query ?? m.calculation_rule ?? '';
      // 收集匹配到的字段 + 保留顺序 + 去重（用数组而非 Set，兼容 es5 target）
      const matched: string[] = [];
      const seen = new Set<string>();
      for (const f of sql.match(FIELD_RE) ?? []) {
        if (!seen.has(f)) { seen.add(f); matched.push(f); }
      }
      metricFields[m.metric_id] = matched;
      matched.forEach((f) => {
        (fieldMetrics[f] ??= []).push(m.metric_id);
      });
    }
    return { metricTables, tableFields, metricFields, fieldMetrics, tableMetrics };
  }, [snap]);

  // 导航触发：选中某个锚点后自动切 Tab + 高亮
  useEffect(() => {
    if (!navTarget || !snap) return;
    if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);

    if (navTarget.type === 'metric') {
      setTab('metrics');
    } else {
      setTab('dimensions');
    }
    // 切 Tab 后等待 DOM 渲染完成再触发高亮
    highlightTimerRef.current = setTimeout(() => {
      const id = navTarget.type === 'metric'
        ? `metric-card-${navTarget.id}`
        : navTarget.type === 'table'
        ? `dim-table-${navTarget.name}`
        : `dim-row-${navTarget.table}-${navTarget.field}`;
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('ring-2', 'ring-blue-500', 'ring-offset-2');
        setTimeout(() => el.classList.remove('ring-2', 'ring-blue-500', 'ring-offset-2'), 2500);
      }
      setNavTarget(null);
    }, 150);
  }, [navTarget, snap]);

  useEffect(() => {
    fetch(`${API_URL}/api/semantic`)
      .then((r) => r.json())
      .then((d) => setSnap(d))
      .catch((e) => showToast('err', `加载失败: ${e.message}`))
      .finally(() => setLoading(false));
  }, []);

  function showToast(type: 'ok' | 'err', msg: string) {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 2500);
  }

  async function handleSave() {
    if (!editing) return;
    const url =
      editKind === 'metric'
        ? `${API_URL}/api/semantic/metrics/${(editing as Metric).metric_id}`
        : `${API_URL}/api/semantic/glossary/${encodeURIComponent((editing as Term).name)}`;
    const body =
      editKind === 'metric'
        ? {
            definition: (editing as Metric).definition,
            calculation_rule: (editing as Metric).calculation_rule,
            example_query: (editing as Metric).example_query ?? '',
          }
        : {
            definition: (editing as Term).definition,
            synonyms: (editing as Term).synonyms,
            related_metrics: (editing as Term).related_metrics,
          };
    try {
      const r = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error((await r.json()).detail || '保存失败');
      showToast('ok', editKind === 'metric' ? '指标口径已更新' : '术语已更新');
      const refreshed = await fetch(`${API_URL}/api/semantic`).then((r) => r.json());
      setSnap(refreshed);
      setEditing(null);
    } catch (e: any) {
      showToast('err', e.message);
    }
  }

  async function runPreview() {
    if (!previewQ.trim()) return;
    setPreviewing(true);
    try {
      const r = await fetch(`${API_URL}/api/semantic/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: previewQ }),
      });
      setPreviewRes(await r.json());
    } catch (e: any) {
      showToast('err', `预览失败: ${e.message}`);
    } finally {
      setPreviewing(false);
    }
  }

  if (loading || !snap) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gac-gray-500 text-sm">加载语义层数据中…</div>
      </div>
    );
  }

  const tabs: { key: TabKey; label: string; icon: string; count: number }[] = [
    { key: 'metrics', label: '指标层', icon: '📊', count: snap.metrics.length },
    { key: 'dimensions', label: '维度层', icon: '🧩', count: snap.dimensions.length },
    { key: 'glossary', label: '同义词层', icon: '📖', count: snap.glossary.length },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="content-card p-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-700 flex items-center justify-center text-white text-xl font-bold">
            🧠
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gac-gray-900">语义层管理</h2>
            <p className="text-sm text-gac-gray-500 mt-1">
              管理 NL2SQL 引擎的指标口径、维度字段、业务同义词——改动后实时生效。
              点击下方指标卡片或维度行，可追踪「指标-维度-数据表」三角映射关系。
            </p>
            <div className="flex items-center gap-4 mt-3 text-xs text-gac-gray-500">
              <span>版本 v{snap.version}</span>
              <span>·</span>
              <span>{snap.domain_group}</span>
              <span>·</span>
              <span className="text-blue-700">🧩 指标 × 维度 × 表 三角映射已启用</span>
            </div>
          </div>
        </div>
      </div>

      {/* 召回预览面板 */}
      <div className="content-card p-5">
        <div className="flex items-center gap-3 mb-3">
          <h3 className="text-base font-semibold text-gac-gray-900">🔍 召回效果预览</h3>
          <span className="text-xs text-gac-gray-500">输入业务问句，模拟当前语义层的召回结果</span>
        </div>
        <div className="flex gap-2 mb-4">
          <input
            value={previewQ}
            onChange={(e) => setPreviewQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runPreview()}
            placeholder="例如：广汽埃安3月销量达成率"
            className="flex-1 px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={runPreview}
            disabled={previewing}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
          >
            {previewing ? '召回中…' : '试一下'}
          </button>
        </div>
        {previewRes && <PreviewResult res={previewRes} />}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-gac-gray-200">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gac-gray-600 hover:text-gac-gray-900'
            }`}
          >
            {t.icon} {t.label}
            <span className="ml-2 px-1.5 py-0.5 bg-gac-gray-100 text-gac-gray-700 rounded text-xs">
              {t.count}
            </span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'metrics' && (
        <MetricsTab
          metrics={snap.metrics}
          map={map}
          onEdit={(m) => { setEditing(m); setEditKind('metric'); }}
          onNavigate={setNavTarget}
        />
      )}
      {tab === 'dimensions' && (
        <DimensionsTab
          dimensions={snap.dimensions}
          map={map}
          onNavigate={setNavTarget}
        />
      )}
      {tab === 'glossary' && (
        <GlossaryTab
          terms={snap.glossary}
          metricMap={Object.fromEntries(snap.metrics.map((m) => [m.metric_id, m.metric_name]))}
          onEdit={(t) => { setEditing(t); setEditKind('term'); }}
        />
      )}

      {/* Edit Modal */}
      {editing && (
        <EditModal
          kind={editKind}
          data={editing}
          onChange={setEditing}
          onClose={() => setEditing(null)}
          onSave={handleSave}
        />
      )}

      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 px-4 py-2 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'ok'
              ? 'bg-emerald-600 text-white'
              : 'bg-red-600 text-white'
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}

// ── 指标层 Tab：突出「指标→表→维度字段」映射关系 ─────────────
function MetricsTab({
  metrics,
  map,
  onEdit,
  onNavigate,
}: {
  metrics: Metric[];
  map: MetricDimMap;
  onEdit: (m: Metric) => void;
  onNavigate: (n: any) => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {metrics.map((m) => {
        const tables = map.metricTables[m.metric_id] ?? [];
        const fields = map.metricFields[m.metric_id] ?? [];
        return (
          <div
            id={`metric-card-${m.metric_id}`}
            key={m.metric_id}
            className="content-card p-4 transition-shadow"
          >
            <div
              className="flex items-start justify-between mb-2 cursor-pointer hover:opacity-80"
              onClick={() => onEdit(m)}
            >
              <div>
                <span className="text-xs font-mono px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                  {m.metric_id}
                </span>
                <h4 className="text-base font-semibold text-gac-gray-900 mt-2">{m.metric_name}</h4>
                <span className="text-xs text-gac-gray-500">{m.business_domain} · {m.unit}</span>
              </div>
              {m._modified_fields && m._modified_fields.length > 0 && (
                <span className="text-xs px-2 py-0.5 bg-amber-50 text-amber-700 rounded">
                  已编辑
                </span>
              )}
            </div>

            <p
              className="text-xs text-gac-gray-600 line-clamp-3 mb-2 cursor-pointer hover:text-gac-gray-900"
              onClick={() => onEdit(m)}
            >
              {m.definition}
            </p>

            <div
              className="text-xs font-mono text-gac-gray-500 bg-gac-gray-50 rounded px-2 py-1 truncate mb-3 cursor-pointer"
              onClick={() => onEdit(m)}
              title={m.calculation_rule}
            >
              {m.calculation_rule}
            </div>

            {/* 🧩 三角映射：涉及表 */}
            {tables.length > 0 && (
              <div className="mb-2">
                <div className="text-xs text-gac-gray-500 mb-1 flex items-center gap-1">
                  <span>📋</span><span>涉及数据表：</span>
                  <span className="text-gac-gray-400">{tables.length} 张</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {tables.map((t) => (
                    <button
                      key={t}
                      onClick={(e) => { e.stopPropagation(); onNavigate({ type: 'table', name: t }); }}
                      className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:underline rounded font-mono transition-colors"
                      title={`跳转到维度层 ${t}`}
                    >
                      {t} →
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 🧩 三角映射：涉及维度字段（从 example_query 自动抽取） */}
            {fields.length > 0 && (
              <div className="mb-2">
                <div className="text-xs text-gac-gray-500 mb-1 flex items-center gap-1">
                  <span>🔍</span><span>涉及维度字段：</span>
                  <span className="text-gac-gray-400">{fields.length} 个</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {fields.map((f) => (
                    <button
                      key={f}
                      onClick={(e) => {
                        e.stopPropagation();
                        const targetTable = tables.find(t => (map.tableFields[t] ?? []).includes(f));
                        if (targetTable) onNavigate({ type: 'field', table: targetTable, field: f });
                      }}
                      className="text-xs px-2 py-0.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 hover:underline rounded font-mono transition-colors"
                      title={`跳转到维度层 ${f} 字段`}
                    >
                      {f} →
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* JOIN 关系提示 */}
            {m.join_condition && tables.length > 1 && (
              <details className="mb-2">
                <summary className="text-xs text-gac-gray-500 cursor-pointer hover:text-gac-gray-900">
                  🔗 表间 JOIN 关系
                </summary>
                <pre className="text-xs font-mono text-gac-gray-700 bg-gray-900 text-green-400 p-2 rounded mt-1 overflow-x-auto whitespace-pre-wrap break-all">
                  {m.join_condition}
                </pre>
              </details>
            )}

            {m._last_modified && (
              <div className="text-xs text-gac-gray-400 mt-2 pt-2 border-t border-gac-gray-100">最近修改：{m._last_modified}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── 维度层 Tab：突出「维度→指标」反向映射 ─────────────────────
function DimensionsTab({
  dimensions,
  map,
  onNavigate,
}: {
  dimensions: Dimension[];
  map: MetricDimMap;
  onNavigate: (n: any) => void;
}) {
  // 按 table 分组
  const grouped = useMemo(() => {
    const g: Record<string, Dimension[]> = {};
    dimensions.forEach((d) => {
      (g[d.table] ??= []).push(d);
    });
    return g;
  }, [dimensions]);

  const tableLabels: Record<string, { name: string; domain: string }> = {
    fact_sales_daily: { name: '整车销售事实表', domain: '整车销售' },
    dim_budget_target: { name: '经营预算表', domain: '经营财务' },
    fact_marketing_expenses: { name: '市场营销事实表', domain: '市场营销' },
  };

  return (
    <div className="space-y-4">
      <div className="content-card p-5 border-l-4 border-l-indigo-500">
        <div className="flex items-center gap-2">
          <span className="text-xl">🧩</span>
          <h3 className="text-base font-semibold text-gac-gray-900">
            维度层 · {dimensions.length} 个字段 × {Object.keys(grouped).length} 张表
          </h3>
          <span className="text-xs text-gac-gray-500 ml-auto">
            自动从 schema 抽取 · 只读
          </span>
        </div>
        <p className="text-xs text-gac-gray-500 mt-1">
          维度是指标的「切片维度」（如品牌、车型、区域、渠道），用于下钻与分组聚合。
          点击下方标签可反向跳回指标层。
        </p>
      </div>
      {Object.entries(grouped).map(([table, dims]) => {
        const referencedMetricIds = map.tableMetrics[table] ?? [];
        return (
          <div id={`dim-table-${table}`} key={table} className="content-card overflow-hidden">
            <div className="px-4 py-3 bg-gac-gray-50 border-b border-gac-gray-200 flex items-center justify-between flex-wrap gap-2">
              <div>
                <h4 className="text-sm font-semibold text-gac-gray-900">
                  {tableLabels[table]?.name || table}
                </h4>
                <span className="text-xs text-gac-gray-500 font-mono">{table}</span>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                  {tableLabels[table]?.domain} · {dims.length} 字段
                </span>
                {/* 🧩 反向映射：表被哪些指标引用 */}
                {referencedMetricIds.length > 0 && (
                  <span className="text-xs px-2 py-0.5 bg-amber-50 text-amber-700 rounded flex items-center gap-1">
                    <span>📊 被</span>
                    {referencedMetricIds.map((mid) => (
                      <button
                        key={mid}
                        onClick={() => onNavigate({ type: 'metric', id: mid })}
                        className="font-mono font-medium hover:underline"
                        title={`跳回指标 ${mid}`}
                      >
                        {mid}
                      </button>
                    ))}
                    <span>引用</span>
                  </span>
                )}
              </div>
            </div>
            <div className="divide-y divide-gac-gray-100">
              {dims.map((d) => {
                const referencedBy = map.fieldMetrics[d.field] ?? [];
                return (
                  <div
                    id={`dim-row-${d.table}-${d.field}`}
                    key={`${d.table}.${d.field}`}
                    className="px-4 py-3 flex items-start gap-3 flex-wrap"
                  >
                    <span className="text-xs font-mono text-blue-700 bg-blue-50 px-2 py-0.5 rounded flex-shrink-0">
                      {d.field}
                    </span>
                    <span className="text-xs text-gac-gray-500 font-mono flex-shrink-0 w-24">
                      {d.type}
                    </span>
                    <span className="text-xs text-gac-gray-700 flex-1 min-w-[200px]">{d.description}</span>
                    {d.synonyms.length > 0 && (
                      <div className="flex gap-1 flex-wrap max-w-xs">
                        {d.synonyms.slice(0, 3).map((s) => (
                          <span
                            key={s}
                            className="text-xs px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                    {/* 🧩 反向映射：字段被哪些指标引用 */}
                    {referencedBy.length > 0 && (
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <span className="text-xs text-gac-gray-400">→</span>
                        {referencedBy.map((mid) => (
                          <button
                            key={mid}
                            onClick={() => onNavigate({ type: 'metric', id: mid })}
                            className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:underline rounded font-mono transition-colors"
                            title={`跳回指标 ${mid}`}
                          >
                            {mid}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function GlossaryTab({
  terms,
  metricMap,
  onEdit,
}: {
  terms: Term[];
  metricMap: Record<string, string>;
  onEdit: (t: Term) => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {terms.map((t) => (
        <div
          key={t.name}
          className="content-card p-4 hover:shadow-md transition-shadow cursor-pointer"
          onClick={() => onEdit(t)}
        >
          <div className="flex items-start justify-between mb-2">
            <h4 className="text-base font-semibold text-gac-gray-900">{t.name}</h4>
            {t._modified_fields && t._modified_fields.length > 0 && (
              <span className="text-xs px-2 py-0.5 bg-amber-50 text-amber-700 rounded">
                已编辑
              </span>
            )}
          </div>
          <p className="text-xs text-gac-gray-600 line-clamp-2 mb-3">{t.definition}</p>
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <span className="text-xs text-gac-gray-500 flex-shrink-0 w-16">同义词</span>
              <div className="flex flex-wrap gap-1">
                {t.synonyms.map((s) => (
                  <span
                    key={s}
                    className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-xs text-gac-gray-500 flex-shrink-0 w-16">关联指标</span>
              <div className="flex flex-wrap gap-1">
                {t.related_metrics.map((mid) => (
                  <span
                    key={mid}
                    className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded font-mono"
                    title={metricMap[mid]}
                  >
                    {mid} {metricMap[mid] && `· ${metricMap[mid]}`}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function PreviewResult({ res }: { res: any }) {
  const hasMatch = res.matched_metrics?.length > 0 || res.matched_terms?.length > 0;
  return (
    <div className="space-y-3 text-sm">
      <div className="text-xs text-gac-gray-500">问句：<span className="text-gac-gray-900 font-medium">{res.query}</span></div>
      {!hasMatch && (
        <div className="text-xs text-amber-700 bg-amber-50 px-3 py-2 rounded">
          ⚠️ 未命中任何指标或术语。可在下方补充同义词/关联，让召回更准。
        </div>
      )}
      {res.matched_metrics?.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-gac-gray-700 mb-2">
            命中指标（{res.matched_metrics.length}）
          </div>
          {res.matched_metrics.map((m: any) => (
            <div key={m.metric_id} className="mb-2 p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <div>
                  <span className="text-xs font-mono px-2 py-0.5 bg-blue-100 text-blue-700 rounded mr-2">
                    {m.metric_id}
                  </span>
                  <span className="text-sm font-medium text-gac-gray-900">{m.metric_name}</span>
                  <span className="text-xs text-gac-gray-500 ml-2">· {m.business_domain}</span>
                </div>
                <span className="text-xs font-mono text-blue-700">score: {m.score}</span>
              </div>
              {m.reasons?.length > 0 && (
                <div className="text-xs text-gac-gray-600 mt-1">
                  命中原因：{m.reasons.join('；')}
                </div>
              )}
            </div>
          ))}
          {res.sample_sql && (
            <details className="mt-2">
              <summary className="text-xs text-blue-700 cursor-pointer hover:underline">
                查看示例 SQL
              </summary>
              <pre className="text-xs font-mono text-gac-gray-700 bg-gac-gray-900 text-green-400 p-3 rounded mt-1 overflow-x-auto">
                {res.sample_sql}
              </pre>
            </details>
          )}
        </div>
      )}
      {res.matched_terms?.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-gac-gray-700 mb-2">
            命中术语（{res.matched_terms.length}）
          </div>
          {res.matched_terms.map((t: any) => (
            <div key={t.name} className="mb-2 p-3 bg-purple-50 rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gac-gray-900">{t.name}</span>
                <span className="text-xs font-mono text-purple-700">score: {t.score}</span>
              </div>
              <div className="text-xs text-gac-gray-600">{t.definition}</div>
              {t.reasons?.length > 0 && (
                <div className="text-xs text-gac-gray-500 mt-1">
                  命中：{t.reasons.join('；')}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EditModal({
  kind,
  data,
  onChange,
  onClose,
  onSave,
}: {
  kind: 'metric' | 'term';
  data: Metric | Term;
  onChange: (d: any) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  const isMetric = kind === 'metric';
  const m = data as Metric;
  const t = data as Term;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-gac-gray-200 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-gac-gray-900">
              {isMetric ? `编辑指标 · ${m.metric_id} ${m.metric_name}` : `编辑术语 · ${t.name}`}
            </h3>
            <p className="text-xs text-gac-gray-500 mt-1">改动后立即写入 JSON 文件，运行时生效</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gac-gray-100 text-gac-gray-500"
          >
            ✕
          </button>
        </div>
        <div className="p-6 space-y-4">
          {isMetric ? (
            <>
              <Field label="业务定义（definition）">
                <textarea
                  value={m.definition}
                  onChange={(e) => onChange({ ...m, definition: e.target.value })}
                  rows={4}
                  className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </Field>
              <Field label="计算规则（calculation_rule）">
                <textarea
                  value={m.calculation_rule}
                  onChange={(e) => onChange({ ...m, calculation_rule: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </Field>
              <Field label="示例 SQL（example_query）">
                <textarea
                  value={m.example_query ?? ''}
                  onChange={(e) => onChange({ ...m, example_query: e.target.value })}
                  rows={5}
                  className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </Field>
              <div className="text-xs text-gac-gray-500">
                ℹ️ 不可改：metric_id / metric_name / business_domain / unit / required_tables / join_condition
              </div>
            </>
          ) : (
            <>
              <Field label="术语定义（definition）">
                <textarea
                  value={t.definition}
                  onChange={(e) => onChange({ ...t, definition: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </Field>
              <Field label="同义词（逗号分隔）">
                <input
                  type="text"
                  value={t.synonyms.join('、')}
                  onChange={(e) =>
                    onChange({
                      ...t,
                      synonyms: e.target.value.split(/[、,，]/).map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </Field>
              <Field label="关联指标（逗号分隔，例：M01, M03）">
                <input
                  type="text"
                  value={t.related_metrics.join('、')}
                  onChange={(e) =>
                    onChange({
                      ...t,
                      related_metrics: e.target.value.split(/[、,，]/).map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </Field>
              <div className="text-xs text-gac-gray-500">ℹ️ 不可改：name</div>
            </>
          )}
        </div>
        <div className="px-6 py-4 border-t border-gac-gray-200 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gac-gray-700 hover:bg-gac-gray-100 rounded-lg"
          >
            取消
          </button>
          <button
            onClick={onSave}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gac-gray-700 mb-1">{label}</label>
      {children}
    </div>
  );
}
