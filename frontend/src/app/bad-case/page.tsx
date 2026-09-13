'use client';

import { useEffect, useState } from 'react';
import { useRole } from '@/contexts/RoleContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface BadCase {
  id: string;
  ts: string;
  actor: string;
  query: string;
  sql_text: string | null;
  result_summary: string | null;
  feedback_type: 'positive' | 'negative' | 'correction';
  feedback_label: string | null;
  correction: string | null;
  resolved: boolean;
  resolved_by: string | null;
  resolved_at: string | null;
  semantic_term_id: string | null;
}

interface Stats {
  total: number;
  resolved: number;
  open: number;
  by_type: { feedback_type: string; count: number }[];
  by_label: { feedback_label: string; count: number }[];
}

const TYPE_META = {
  positive:   { label: '👍 采纳', color: 'emerald', icon: '👍' },
  negative:   { label: '👎 不采纳', color: 'orange', icon: '👎' },
  correction: { label: '📝 修正', color: 'blue', icon: '📝' },
};

export default function BadCasePage() {
  const { role, roleInfo } = useRole();
  const [items, setItems] = useState<BadCase[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'open' | 'resolved'>('open');
  const [resolving, setResolving] = useState<string | null>(null);

  async function fetchData() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filter === 'open') params.append('resolved', 'false');
      if (filter === 'resolved') params.append('resolved', 'true');
      params.append('limit', '100');

      const [listRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/api/bad-case/list?${params}`),
        fetch(`${API_URL}/api/bad-case/stats`),
      ]);
      setItems((await listRes.json()).items || []);
      setStats(await statsRes.json());
    } finally {
      setLoading(false);
    }
  }

  async function resolveCase(caseId: string) {
    setResolving(caseId);
    try {
      const r = await fetch(`${API_URL}/api/bad-case/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: caseId, resolved_by: role }),
      });
      if (r.ok) {
        // 派发通知
        window.dispatchEvent(
          new CustomEvent('gac-notification', {
            detail: {
              type: 'badcase_feedback',
              severity: 'success',
              title: '✅ Bad Case 已闭环',
              body: '已加入语义层，下同类问数会更准',
              link: '/bad-case',
              audience: ['analyst', 'product'],
            },
          })
        );
        await fetchData();
      }
    } finally {
      setResolving(null);
    }
  }

  useEffect(() => {
    fetchData();
  }, [filter]);

  const canResolve = ['analyst', 'product'].includes(role);

  return (
    <div className="p-6 max-w-6xl mx-auto" data-tour="badcase-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gac-gray-900 flex items-center gap-2">
            🐛 Bad Case 收件箱
          </h1>
          <p className="text-sm text-gac-gray-500 mt-1">
            用户采纳/不采纳/修正反馈 · 一键闭环关联语义层（仅 {roleInfo.label} 可闭环）
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? '加载中…' : '🔄 刷新'}
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <StatCard label="总反馈数" value={stats.total} icon="💬" color="blue" />
          <StatCard label="待处理" value={stats.open} icon="🔔" color="orange" />
          <StatCard label="已闭环" value={stats.resolved} icon="✅" color="emerald" />
          <StatCard label="闭环率" value={stats.total ? Math.round((stats.resolved / stats.total) * 100) : 0} suffix="%" icon="📈" color="purple" />
        </div>
      )}

      {/* 分布 */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <DistCard title="按反馈类型" items={stats.by_type.map((i) => ({ ...i, label: TYPE_META[i.feedback_type as keyof typeof TYPE_META]?.label || i.feedback_type }))} />
          <DistCard title="Top 问题标签" items={stats.by_label} />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gac-gray-200">
        {(['open', 'resolved', 'all'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              filter === t
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gac-gray-500 hover:text-gac-gray-700'
            }`}
          >
            {t === 'open' ? '🔔 待处理' : t === 'resolved' ? '✅ 已闭环' : '📋 全部'}
          </button>
        ))}
      </div>

      {/* Cards */}
      <div className="space-y-3">
        {items.map((it) => {
          const meta = TYPE_META[it.feedback_type] || TYPE_META.negative;
          return (
            <div key={it.id} className="content-card p-4">
              <div className="flex items-start gap-3">
                <span className="text-2xl flex-shrink-0">{meta.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium bg-${meta.color}-100 text-${meta.color}-700`}>
                      {meta.label}
                    </span>
                    {it.feedback_label && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-gac-gray-100 text-gac-gray-700">
                        {it.feedback_label}
                      </span>
                    )}
                    {it.resolved && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">
                        ✅ {it.resolved_by} 已闭环
                      </span>
                    )}
                    <span className="text-[10px] text-gac-gray-400 font-mono">
                      {new Date(it.ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="text-sm font-medium text-gac-gray-900 mb-1">
                    {it.actor}：{it.query}
                  </div>
                  {it.correction && (
                    <div className="text-xs text-gac-gray-700 bg-blue-50 px-2 py-1.5 rounded mt-1.5">
                      📝 修正口径：{it.correction}
                    </div>
                  )}
                  {it.sql_text && (
                    <details className="mt-1.5">
                      <summary className="text-[10px] text-gac-gray-400 cursor-pointer hover:text-gac-gray-600">
                        查看生成的 SQL
                      </summary>
                      <pre className="text-[10px] bg-gac-gray-50 px-2 py-1.5 rounded mt-1 overflow-x-auto">
{it.sql_text}
                      </pre>
                    </details>
                  )}
                  {it.semantic_term_id && (
                    <div className="text-xs text-purple-600 mt-1">
                      🔗 关联语义层 term：<span className="font-mono">{it.semantic_term_id}</span>
                    </div>
                  )}
                </div>
                {!it.resolved && canResolve && (
                  <button
                    onClick={() => resolveCase(it.id)}
                    disabled={resolving === it.id}
                    className="flex-shrink-0 px-3 py-1.5 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {resolving === it.id ? '闭环中…' : '✅ 一键闭环'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
        {items.length === 0 && !loading && (
          <div className="text-center py-16 text-gac-gray-400">
            <div className="text-3xl mb-2">📭</div>
            <div className="text-xs">暂无{filter === 'open' ? '待处理' : ''}反馈</div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, suffix, icon, color }: { label: string; value: number; suffix?: string; icon: string; color: string }) {
  return (
    <div className={`bg-${color}-50 border border-${color}-100 rounded-xl p-3`}>
      <div className="flex items-center justify-between">
        <div className="text-xs text-gac-gray-600">{label}</div>
        <div className="text-xl">{icon}</div>
      </div>
      <div className={`text-2xl font-bold text-${color}-700 mt-1`}>
        {value}
        {suffix && <span className="text-sm ml-0.5">{suffix}</span>}
      </div>
    </div>
  );
}

function DistCard({ title, items }: { title: string; items: { count: number; label?: string; feedback_type?: string; feedback_label?: string }[] }) {
  const max = Math.max(...items.map((i) => i.count), 1);
  return (
    <div className="content-card p-3">
      <div className="text-xs font-medium text-gac-gray-600 mb-2">{title}</div>
      <div className="space-y-1.5">
        {items.slice(0, 6).map((it, i) => {
          const label = it.label || it.feedback_label || it.feedback_type || '-';
          return (
            <div key={i} className="flex items-center gap-2 text-xs">
              <div className="w-24 truncate text-gac-gray-700">{label}</div>
              <div className="flex-1 h-1.5 bg-gac-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(it.count / max) * 100}%` }} />
              </div>
              <div className="w-8 text-right text-gac-gray-500 font-mono">{it.count}</div>
            </div>
          );
        })}
        {items.length === 0 && (
          <div className="text-xs text-gac-gray-400 text-center py-2">暂无数据</div>
        )}
      </div>
    </div>
  );
}
