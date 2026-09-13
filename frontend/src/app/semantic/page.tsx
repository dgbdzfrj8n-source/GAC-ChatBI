'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';

const API_URL =
  typeof window !== 'undefined'
    ? localStorage.getItem('apiUrl') || process.env.NEXT_PUBLIC_API_URL || 'https://gac-chatbi-api.onrender.com'
    : process.env.NEXT_PUBLIC_API_URL || 'https://gac-chatbi-api.onrender.com';

interface Metric {
  metric_id: string;
  metric_name: string;
  business_domain: string;
  definition: string;
  unit: string;
  calculation_rule: string;
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

export default function SemanticLayerPage() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [tab, setTab] = useState<TabKey>('metrics');
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Metric | Term | null>(null);
  const [editKind, setEditKind] = useState<'metric' | 'term'>('metric');
  const [toast, setToast] = useState<{ type: 'ok' | 'err'; msg: string } | null>(null);

  // 预览
  const [previewQ, setPreviewQ] = useState('广汽埃安3月销量达成率');
  const [previewRes, setPreviewRes] = useState<any>(null);
  const [previewing, setPreviewing] = useState(false);

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
      // 重新加载
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
              维度层自动从 schema 抽取；指标与同义词可点击编辑。
            </p>
            <div className="flex items-center gap-4 mt-3 text-xs text-gac-gray-500">
              <span>版本 v{snap.version}</span>
              <span>·</span>
              <span>{snap.domain_group}</span>
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
          onEdit={(m) => {
            setEditing(m);
            setEditKind('metric');
          }}
        />
      )}
      {tab === 'dimensions' && (
        <DimensionsTab dimensions={snap.dimensions} embedded={false} />
      )}
      {tab === 'glossary' && (
        <GlossaryTab
          terms={snap.glossary}
          metricMap={Object.fromEntries(snap.metrics.map((m) => [m.metric_id, m.metric_name]))}
          onEdit={(t) => {
            setEditing(t);
            setEditKind('term');
          }}
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

function MetricsTab({ metrics, onEdit }: { metrics: Metric[]; onEdit: (m: Metric) => void }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {metrics.map((m) => (
        <div
          key={m.metric_id}
          className="content-card p-4 hover:shadow-md transition-shadow cursor-pointer"
          onClick={() => onEdit(m)}
        >
          <div className="flex items-start justify-between mb-2">
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
          <p className="text-xs text-gac-gray-600 line-clamp-3 mb-2">{m.definition}</p>
          <div className="text-xs font-mono text-gac-gray-500 bg-gac-gray-50 rounded px-2 py-1 truncate">
            {m.calculation_rule}
          </div>
          {m._last_modified && (
            <div className="text-xs text-gac-gray-400 mt-2">最近修改：{m._last_modified}</div>
          )}
        </div>
      ))}
    </div>
  );
}

function DimensionsTab({ dimensions, embedded = false }: { dimensions: Dimension[]; embedded?: boolean }) {
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
      {/* 独立 Tab 模式下显示完整头部（合并 Tab 模式下不显示，因为上面已有大标题） */}
      {!embedded && (
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
          </p>
        </div>
      )}
      {Object.entries(grouped).map(([table, dims]) => (
        <div key={table} className="content-card overflow-hidden">
          <div className="px-4 py-3 bg-gac-gray-50 border-b border-gac-gray-200 flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-gac-gray-900">
                {tableLabels[table]?.name || table}
              </h4>
              <span className="text-xs text-gac-gray-500 font-mono">{table}</span>
            </div>
            <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
              {tableLabels[table]?.domain} · {dims.length} 字段
            </span>
          </div>
          <div className="divide-y divide-gac-gray-100">
            {dims.map((d) => (
              <div key={`${d.table}.${d.field}`} className="px-4 py-3 flex items-start gap-3">
                <span className="text-xs font-mono text-blue-700 bg-blue-50 px-2 py-0.5 rounded flex-shrink-0">
                  {d.field}
                </span>
                <span className="text-xs text-gac-gray-500 font-mono flex-shrink-0 w-24">
                  {d.type}
                </span>
                <span className="text-xs text-gac-gray-700 flex-1">{d.description}</span>
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
              </div>
            ))}
          </div>
        </div>
      ))}
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
