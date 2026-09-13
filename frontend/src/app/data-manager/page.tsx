'use client';

import { useEffect, useState, useRef } from 'react';

// 优先使用构建期注入的 NEXT_PUBLIC_API_URL，fallback 到 localhost（本地开发）
// 用户也可以在浏览器 localStorage 里手动覆盖（key: apiUrl）
const API_URL =
  typeof window !== 'undefined'
    ? localStorage.getItem('apiUrl') ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000'
    : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ColumnInfo {
  name: string;
  type: string;
}

interface UserTable {
  table_name: string;
  row_count: number;
  column_count: number;
  columns: ColumnInfo[];
  error?: string;
}

interface DefaultTable {
  table_name: string;
  label: string;
  domain: string;
  icon: string;
  is_default: boolean;
  row_count: number;
  column_count: number;
  columns: ColumnInfo[];
  error?: string;
}

interface Stats {
  table_count: number;
  total_rows: number;
  db_size_bytes: number;
  csv_size_bytes: number;
  quota: {
    max_tables: number;
    max_rows_per_table: number;
    max_file_size_bytes: number;
  };
  tables: string[];
}

export default function DataManagerPage() {
  const [tables, setTables] = useState<UserTable[]>([]);
  const [defaultTables, setDefaultTables] = useState<any[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewing, setPreviewing] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<{
    table: string;
    columns: string[];
    data: any[];
    row_count: number;
  } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState<{ type: 'ok' | 'err'; msg: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    refresh();
  }, []);

  function showToast(type: 'ok' | 'err', msg: string) {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 2500);
  }

  async function refresh() {
    setLoading(true);
    try {
      const [a, b, c] = await Promise.all([
        fetch(`${API_URL}/api/data/uploads`).then((r) => r.json()),
        fetch(`${API_URL}/api/data/stats`).then((r) => r.json()),
        fetch(`${API_URL}/api/data/default-tables`).then((r) => r.json()),
      ]);
      setTables(a.tables || []);
      setStats(b);
      setDefaultTables(c.tables || []);
    } catch (e: any) {
      showToast('err', `加载失败: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  /**
   * 跳转到智能对话并自动提问该表的明细
   * 用更明确的查询模板，让 NL2SQL 能稳定命中"明细查看"意图
   */
  function handleAskInChat(tableName: string) {
    const query = `请按日期倒序展示 ${tableName} 表的前 20 行数据明细（用 SQL: SELECT * FROM ${tableName} ORDER BY <时间列> DESC LIMIT 20）`;
    if (typeof window !== 'undefined') {
      localStorage.setItem('gac-pending-query', query);
      window.location.href = '/?pending=' + encodeURIComponent(query);
    }
  }

  async function handleUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const file = form.get('file') as File | null;
    if (!file || file.size === 0) {
      showToast('err', '请选择 CSV 文件');
      return;
    }
    if (file.size > (stats?.quota.max_file_size_bytes || 20 * 1024 * 1024)) {
      showToast('err', `文件过大（${(file.size / 1024 / 1024).toFixed(1)}MB > 20MB）`);
      return;
    }
    setUploading(true);
    try {
      const r = await fetch(`${API_URL}/api/data/upload`, {
        method: 'POST',
        body: form,
      });
      const result = await r.json();
      if (!r.ok) throw new Error(result.detail || '上传失败');
      showToast('ok', `导入成功: ${result.table_name}（${result.row_count} 行）`);
      if (fileRef.current) fileRef.current.value = '';
      (e.target as HTMLFormElement).reset();
      await refresh();
    } catch (e: any) {
      showToast('err', e.message);
    } finally {
      setUploading(false);
    }
  }

  async function handlePreview(tname: string, source: 'user' | 'business' = 'user') {
    setPreviewing(tname);
    try {
      const r = await fetch(
        `${API_URL}/api/data/preview/${encodeURIComponent(tname)}?limit=100&source=${source}`
      );
      const result = await r.json();
      if (!r.ok) throw new Error(result.detail || '预览失败');
      setPreviewData(result);
    } catch (e: any) {
      showToast('err', e.message);
    } finally {
      setPreviewing(null);
    }
  }

  async function handleExport(tname: string) {
    try {
      const r = await fetch(`${API_URL}/api/data/export/${encodeURIComponent(tname)}`);
      if (!r.ok) {
        const e = await r.json();
        throw new Error(e.detail || '导出失败');
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${tname}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('ok', `已导出 ${tname}.csv`);
    } catch (e: any) {
      showToast('err', e.message);
    }
  }

  async function handleDelete(tname: string) {
    if (!confirm(`确定删除用户表 ${tname} ？此操作不可恢复。`)) return;
    try {
      const r = await fetch(`${API_URL}/api/data/${encodeURIComponent(tname)}`, {
        method: 'DELETE',
      });
      const result = await r.json();
      if (!r.ok) throw new Error(result.detail || '删除失败');
      showToast('ok', `已删除 ${tname}`);
      setPreviewData(null);
      await refresh();
    } catch (e: any) {
      showToast('err', e.message);
    }
  }

  function fmtBytes(b: number) {
    if (b < 1024) return `${b} B`;
    if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
    return `${(b / 1024 / 1024).toFixed(2)} MB`;
  }

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-96 text-gac-gray-500 text-sm">
        加载数据管理面板…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="content-card p-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center text-white text-2xl">
            🗄️
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gac-gray-900">数据管理</h2>
            <p className="text-sm text-gac-gray-500 mt-1">
              上传业务 CSV 文件，自动建表装载到独立 DuckDB 库。可预览、下载、删除。
              业务主库严格只读，用户数据完全隔离。
            </p>
            {stats && (
              <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-gac-gray-500">
                <span>
                  📊 <b className="text-gac-gray-900">{stats.table_count}</b> 个用户表 / 共{' '}
                  <b className="text-gac-gray-900">{stats.total_rows.toLocaleString()}</b> 行
                </span>
                <span>·</span>
                <span>💾 DB {fmtBytes(stats.db_size_bytes)}</span>
                <span>·</span>
                <span>📁 CSV 归档 {fmtBytes(stats.csv_size_bytes)}</span>
                <span>·</span>
                <span>
                  配额: {stats.quota.max_tables} 表 · {stats.quota.max_rows_per_table.toLocaleString()} 行/表 ·{' '}
                  {Math.round(stats.quota.max_file_size_bytes / 1024 / 1024)}MB/文件
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Upload Form */}
      <div className="content-card p-5">
        <h3 className="text-base font-semibold text-gac-gray-900 mb-3">
          📤 上传 CSV 文件
        </h3>
        <form onSubmit={handleUpload} className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-gac-gray-600 mb-1">CSV 文件</label>
            <input
              ref={fileRef}
              type="file"
              name="file"
              accept=".csv,text/csv"
              required
              className="w-full text-sm text-gac-gray-700 file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 file:cursor-pointer"
            />
          </div>
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs text-gac-gray-600 mb-1">目标表名（自动加 user_ 前缀）</label>
            <input
              type="text"
              name="table_name"
              required
              placeholder="例：4月新能源销量明细"
              pattern="[\w\u4e00-\u9fa5\-]{2,40}"
              className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <button
            type="submit"
            disabled={uploading}
            className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
          >
            {uploading ? '上传中…' : '上传并建表'}
          </button>
        </form>
        <div className="mt-2 text-xs text-gac-gray-500">
          💡 智能识别：自动检测表头、数字/日期类型推断、中文列名兼容、支持 UTF-8 与 GBK 编码。
        </div>
      </div>

      {/* Tables List */}
      <div className="content-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-gac-gray-900">
            📋 用户表清单
            <span className="ml-2 text-xs text-gac-gray-500">({tables.length})</span>
          </h3>
          <button
            onClick={refresh}
            disabled={loading}
            className="text-xs px-3 py-1.5 text-emerald-700 hover:bg-emerald-50 rounded-lg transition-colors"
          >
            🔄 刷新
          </button>
        </div>

        {tables.length === 0 ? (
          <div className="py-12 text-center text-gac-gray-400 text-sm">
            <div className="text-3xl mb-2">📭</div>
            暂无用户上传的数据。上传第一个 CSV 试试。
          </div>
        ) : (
          <div className="space-y-3">
            {tables.map((t) => (
              <div
                key={t.table_name}
                className="border border-gac-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-mono text-sm font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                        {t.table_name}
                      </span>
                      <span className="text-xs text-gac-gray-500">
                        {t.row_count?.toLocaleString() || '?'} 行 · {t.column_count || '?'} 列
                      </span>
                    </div>
                    {t.columns && (
                      <div className="flex flex-wrap gap-1">
                        {t.columns.slice(0, 8).map((c) => (
                          <span
                            key={c.name}
                            className="text-xs px-1.5 py-0.5 bg-gac-gray-50 text-gac-gray-700 rounded font-mono"
                            title={c.type}
                          >
                            {c.name}
                            <span className="ml-1 text-gac-gray-400">{c.type}</span>
                          </span>
                        ))}
                        {t.columns.length > 8 && (
                          <span className="text-xs text-gac-gray-400">+{t.columns.length - 8}</span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={() => handlePreview(t.table_name)}
                      disabled={previewing === t.table_name}
                      className="px-2.5 py-1.5 text-xs text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-md disabled:opacity-50 transition-colors"
                    >
                      {previewing === t.table_name ? '加载…' : '👁 预览'}
                    </button>
                    <button
                      onClick={() => handleAskInChat(t.table_name)}
                      className="px-2.5 py-1.5 text-xs text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-md transition-colors"
                      title="跳转到智能对话查看数据明细"
                    >
                      🔍 明细
                    </button>
                    <button
                      onClick={() => handleExport(t.table_name)}
                      className="px-2.5 py-1.5 text-xs text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-md transition-colors"
                    >
                      ⬇ 导出
                    </button>
                    <button
                      onClick={() => handleDelete(t.table_name)}
                      className="px-2.5 py-1.5 text-xs text-red-600 bg-red-50 hover:bg-red-100 rounded-md transition-colors"
                    >
                      🗑 删除
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 业务主库默认表（开箱即用 · 只读 · 不占用户配额） */}
      <div className="content-card p-5 border-l-4 border-l-blue-500">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-semibold text-gac-gray-900 flex items-center gap-2">
              📚 业务主库默认表
              <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded font-mono">
                {defaultTables.length} 张
              </span>
            </h3>
            <p className="text-xs text-gac-gray-500 mt-1">
              这些是广汽集团经营分析内置的 3 张事实表，开箱即用，只读。点击「明细」可直接在智能对话中查询。
            </p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {defaultTables.map((t) => (
            <div
              key={t.table_name}
              className="border border-blue-100 bg-gradient-to-br from-blue-50/50 to-white rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">{t.icon || '📊'}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-sm text-gac-gray-900 truncate">
                    {t.label || t.table_name}
                  </div>
                  <div className="font-mono text-xs text-gac-gray-500 truncate">
                    {t.table_name}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-1 mb-3">
                <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                  {t.domain}
                </span>
                <span className="text-xs px-1.5 py-0.5 bg-gac-gray-100 text-gac-gray-700 rounded">
                  {t.row_count?.toLocaleString() || 0} 行
                </span>
                <span className="text-xs px-1.5 py-0.5 bg-gac-gray-100 text-gac-gray-700 rounded">
                  {t.column_count || 0} 列
                </span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handlePreview(t.table_name, 'business')}
                  disabled={previewing === t.table_name}
                  className="flex-1 px-2 py-1.5 text-xs text-blue-700 bg-white border border-blue-200 hover:bg-blue-50 rounded-md disabled:opacity-50 transition-colors"
                >
                  👁 预览
                </button>
                <button
                  onClick={() => handleAskInChat(t.table_name)}
                  className="flex-1 px-2 py-1.5 text-xs text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors font-medium"
                  title="跳转到智能对话查看数据明细"
                >
                  🔍 明细（→ Chat）
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Preview Modal */}
      {previewData && (
        <div
          className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
          onClick={() => setPreviewData(null)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-gac-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-gac-gray-900 font-mono">
                  {previewData.table}
                </h3>
                <p className="text-xs text-gac-gray-500 mt-1">
                  前 {previewData.data.length} 行 / 总 {previewData.row_count} 行 · {previewData.columns.length} 列
                </p>
              </div>
              <button
                onClick={() => setPreviewData(null)}
                className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gac-gray-100 text-gac-gray-500"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gac-gray-50">
                  <tr>
                    {previewData.columns.map((c) => (
                      <th
                        key={c}
                        className="text-left px-3 py-2 text-xs font-medium text-gac-gray-700 border-b border-gac-gray-200 whitespace-nowrap"
                      >
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewData.data.map((row, i) => (
                    <tr key={i} className="hover:bg-gac-gray-50">
                      {previewData.columns.map((c) => (
                        <td
                          key={c}
                          className="px-3 py-2 text-xs text-gac-gray-700 border-b border-gac-gray-100 whitespace-nowrap"
                        >
                          {row[c] === null ? <span className="text-gac-gray-300">null</span> : String(row[c])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 px-4 py-2 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'ok' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}
