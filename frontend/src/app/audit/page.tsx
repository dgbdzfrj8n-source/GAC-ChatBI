'use client';

import { useEffect, useState } from 'react';
import { useRole } from '@/contexts/RoleContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface AuditItem {
  id: string;
  ts: string;
  actor: string;
  action: string;
  resource: string;
  resource_id: string | null;
  payload: Record<string, unknown>;
  ip: string;
  note: string | null;
}

interface Stats {
  total: number;
  today: number;
  by_actor: { actor: string; count: number }[];
  by_action: { action: string; count: number }[];
  by_resource: { resource: string; count: number }[];
}

const ACTION_META: Record<string, { label: string; color: string }> = {
  create:   { label: '创建', color: 'emerald' },
  update:   { label: '更新', color: 'blue' },
  delete:   { label: '删除', color: 'red' },
  query:    { label: '查询', color: 'gac-gray' },
  export:   { label: '导出', color: 'indigo' },
  feedback: { label: '反馈', color: 'orange' },
  login:    { label: '登录', color: 'purple' },
};

const RESOURCE_META: Record<string, { label: string; icon: string }> = {
  semantic_term:  { label: '语义层术语', icon: '📚' },
  metric:         { label: '指标',     icon: '📏' },
  dataset:        { label: '数据集',   icon: '💾' },
  chat:           { label: '问数',     icon: '💬' },
  data_manager:   { label: '数据管理', icon: '⚙️' },
  bad_case:       { label: 'Bad Case', icon: '🐛' },
  system:         { label: '系统',     icon: '🖥️' },
};

function actionMeta(action: string) {
  return ACTION_META[action] || { label: action, color: 'gac-gray' };
}
function resourceMeta(resource: string) {
  return RESOURCE_META[resource] || { label: resource, icon: '📄' };
}

function fmtTime(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

export default function AuditPage() {
  const { role } = useRole();
  const [items, setItems] = useState<AuditItem[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<{ actor: string; action: string; resource: string }>({
    actor: '',
    action: '',
    resource: '',
  });

  async function fetchData() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.actor) params.append('actor', filters.actor);
      if (filters.action) params.append('action', filters.action);
      if (filters.resource) params.append('resource', filters.resource);
      params.append('limit', '200');

      const [listRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/api/audit/list?${params}`),
        fetch(`${API_URL}/api/audit/stats`),
      ]);
      const listData = await listRes.json();
      const statsData = await statsRes.json();
      setItems(listData.items || []);
      setStats(statsData);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (['executive', 'analyst', 'product'].includes(role)) {
      fetchData();
    }
  }, [role, filters]);

  if (!['executive', 'analyst', 'product'].includes(role)) {
    return (
      <div className="p-8 text-center text-gac-gray-500">
        🔒 访客无审计日志权限
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto" data-tour="audit-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gac-gray-900 flex items-center gap-2">
            🔍 操作审计日志
          </h1>
          <p className="text-sm text-gac-gray-500 mt-1">
            记录所有写操作 · 谁、什么时候、改了什么（append-only）
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

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <StatCard label="总记录数" value={stats.total} icon="📊" color="blue" />
          <StatCard label="今日操作" value={stats.today} icon="📅" color="emerald" />
          <StatCard label="涉及角色" value={stats.by_actor.length} icon="👥" color="purple" />
          <StatCard label="资源类型" value={stats.by_resource.length} icon="📦" color="indigo" />
        </div>
      )}

      {/* 分布 */}
      {stats && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <DistCard title="操作分布" items={stats.by_action} renderKey={(i) => i.action} renderLabel={actionMeta} />
          <DistCard title="资源分布" items={stats.by_resource} renderKey={(i) => i.resource} renderLabel={resourceMeta} />
          <DistCard title="活跃角色" items={stats.by_actor} renderKey={(i) => i.actor} />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        <input
          type="text"
          placeholder="按操作者过滤…"
          value={filters.actor}
          onChange={(e) => setFilters({ ...filters, actor: e.target.value })}
          className="px-3 py-1.5 text-xs rounded-lg border border-gac-gray-300 focus:outline-none focus:border-blue-500"
        />
        <select
          value={filters.action}
          onChange={(e) => setFilters({ ...filters, action: e.target.value })}
          className="px-3 py-1.5 text-xs rounded-lg border border-gac-gray-300 bg-white focus:outline-none focus:border-blue-500"
        >
          <option value="">全部动作</option>
          {Object.keys(ACTION_META).map((a) => (
            <option key={a} value={a}>{ACTION_META[a].label}</option>
          ))}
        </select>
        <select
          value={filters.resource}
          onChange={(e) => setFilters({ ...filters, resource: e.target.value })}
          className="px-3 py-1.5 text-xs rounded-lg border border-gac-gray-300 bg-white focus:outline-none focus:border-blue-500"
        >
          <option value="">全部资源</option>
          {Object.keys(RESOURCE_META).map((r) => (
            <option key={r} value={r}>{RESOURCE_META[r].label}</option>
          ))}
        </select>
        {(filters.actor || filters.action || filters.resource) && (
          <button
            onClick={() => setFilters({ actor: '', action: '', resource: '' })}
            className="px-2 py-1.5 text-xs text-gac-gray-600 hover:bg-gac-gray-100 rounded-lg"
          >
            ✕ 清除过滤
          </button>
        )}
      </div>

      {/* 列表 */}
      <div className="content-card overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-gac-gray-50 text-gac-gray-600">
            <tr>
              <th className="px-3 py-2 text-left font-medium">时间</th>
              <th className="px-3 py-2 text-left font-medium">操作者</th>
              <th className="px-3 py-2 text-left font-medium">动作</th>
              <th className="px-3 py-2 text-left font-medium">资源</th>
              <th className="px-3 py-2 text-left font-medium">ID</th>
              <th className="px-3 py-2 text-left font-medium">变更内容</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gac-gray-100">
            {items.map((it) => {
              const am = actionMeta(it.action);
              const rm = resourceMeta(it.resource);
              const payloadStr = Object.keys(it.payload || {}).length > 0
                ? JSON.stringify(it.payload).slice(0, 60) + (JSON.stringify(it.payload).length > 60 ? '…' : '')
                : it.note || '-';
              return (
                <tr key={it.id} className="hover:bg-gac-gray-50">
                  <td className="px-3 py-2 font-mono text-gac-gray-500 whitespace-nowrap">{fmtTime(it.ts)}</td>
                  <td className="px-3 py-2">
                    <span className="px-1.5 py-0.5 rounded bg-gac-gray-100 text-gac-gray-700 font-mono">
                      {it.actor}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium bg-${am.color}-100 text-${am.color}-700`}>
                      {am.label}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-gac-gray-700">{rm.icon} {rm.label}</span>
                  </td>
                  <td className="px-3 py-2 font-mono text-gac-gray-500 text-[10px]">
                    {it.resource_id?.slice(0, 16) || '-'}
                  </td>
                  <td className="px-3 py-2 text-gac-gray-600 max-w-xs truncate" title={JSON.stringify(it.payload)}>
                    {payloadStr}
                  </td>
                </tr>
              );
            })}
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-gac-gray-400">
                  暂无审计记录
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: number; icon: string; color: string }) {
  return (
    <div className={`bg-${color}-50 border border-${color}-100 rounded-xl p-3`}>
      <div className="flex items-center justify-between">
        <div className="text-xs text-gac-gray-600">{label}</div>
        <div className="text-xl">{icon}</div>
      </div>
      <div className={`text-2xl font-bold text-${color}-700 mt-1`}>{value}</div>
    </div>
  );
}

function DistCard<T>({
  title,
  items,
  renderKey,
  renderLabel,
}: {
  title: string;
  items: T[];
  renderKey: (item: T) => string;
  renderLabel?: (key: string) => { label: string; color?: string; icon?: string };
}) {
  const max = Math.max(...items.map((i: any) => i.count), 1);
  return (
    <div className="content-card p-3">
      <div className="text-xs font-medium text-gac-gray-600 mb-2">{title}</div>
      <div className="space-y-1.5">
        {items.slice(0, 6).map((it: any, i) => {
          const k = renderKey(it);
          const meta = renderLabel?.(k);
          const label = meta?.label || k;
          const icon = meta?.icon;
          return (
            <div key={i} className="flex items-center gap-2 text-xs">
              <div className="w-20 truncate text-gac-gray-700">
                {icon && <span className="mr-1">{icon}</span>}
                {label}
              </div>
              <div className="flex-1 h-1.5 bg-gac-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${(it.count / max) * 100}%` }}
                />
              </div>
              <div className="w-8 text-right text-gac-gray-500 font-mono">{it.count}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
