'use client';

import { useEffect, useState } from 'react';
import GacBadge from '@/components/GacBadge';

interface HistoryItem {
  id: string;
  query: string;
  timestamp: string;
  brand: string;
  success: boolean;
  /** 新增：SQL + 摘要（用于详情/编辑/导出） */
  sql?: string;
  insight?: string;
  chart_type?: string;
  row_count?: number;
  execution_time_ms?: number;
  /** 用户备注（编辑保存） */
  tags?: string[];
  note?: string;
}

const STORAGE_KEY = 'gac-chatbi-history-v2';  // 用 v2 区分旧 demo 数据

const seedDemoData = (): HistoryItem[] => [
  {
    id: 'demo-1',
    query: '2025年3月埃安销量与预算达成率是多少？',
    timestamp: '2026-09-13 11:23',
    brand: '广汽埃安',
    success: true,
    sql: "WITH s AS (SELECT brand_name, STRFTIME('%Y-%m', sale_date) AS ym, SUM(delivered_units) AS units FROM fact_sales_daily WHERE brand_name='广汽埃安' AND STRFTIME('%Y-%m', sale_date)='2025-03' GROUP BY 1,2) SELECT s.units, b.target_units, ROUND(s.units*100.0/NULLIF(b.target_units,0),2) AS rate FROM s JOIN dim_budget_target b ON s.brand_name=b.brand_name AND s.ym=b.year_month",
    insight: '2025年3月广汽埃安实际完成 4,462 辆，预算 4,615 辆，达成率 96.68%。',
    chart_type: 'table',
    row_count: 1,
    execution_time_ms: 86,
    tags: ['埃安', '月报'],
    note: '高管视角关心的核心指标',
  },
  {
    id: 'demo-2',
    query: '各品牌总交付量与总营收是多少？',
    timestamp: '2026-09-13 11:18',
    brand: '全部',
    success: true,
    sql: 'SELECT brand_name, SUM(delivered_units), ROUND(SUM(gross_revenue)/1e8,2) FROM fact_sales_daily GROUP BY 1',
    insight: '集团三大品牌总交付 X 辆，总营收 Y 亿元。',
    chart_type: 'bar',
    row_count: 3,
    execution_time_ms: 124,
    tags: ['总览'],
  },
  {
    id: 'demo-3',
    query: '抖音渠道的 CPL 在所有渠道里排第几？',
    timestamp: '2026-09-13 11:12',
    brand: '全部',
    success: true,
    sql: 'SELECT channel_name, ROUND(SUM(expense_amount)/NULLIF(SUM(leads_generated),0),1) AS cpl FROM fact_marketing_expenses GROUP BY 1 ORDER BY cpl',
    insight: '抖音 CPL = 32.8 元，排在第 2 位（懂车帝最优）。',
    chart_type: 'bar',
    row_count: 4,
    execution_time_ms: 93,
    tags: ['市场营销', 'CPL'],
  },
  {
    id: 'demo-4',
    query: '传祺 GS8 在华南大区 8 月销量',
    timestamp: '2026-09-13 10:55',
    brand: '广汽传祺',
    success: true,
    sql: "SELECT SUM(delivered_units) FROM fact_sales_daily WHERE brand_name='广汽传祺' AND model_name='传祺GS8' AND region_name='华南区' AND STRFTIME('%Y-%m', sale_date)='2025-03'",
    insight: '传祺 GS8 在华南大区 8 月销量：XXX 辆。',
    chart_type: 'table',
    row_count: 1,
    execution_time_ms: 79,
  },
  {
    id: 'demo-5',
    query: '昊铂 HT 与昊铂 GT 客流转化率对比',
    timestamp: '2026-09-13 10:40',
    brand: '昊铂',
    success: true,
    sql: "SELECT model_name, ROUND(SUM(test_drives)*100.0/NULLIF(SUM(customer_leads),0),2) FROM fact_sales_daily WHERE brand_name='昊铂' GROUP BY 1",
    insight: '昊铂 HT 试驾转化率 13.5%，昊铂 GT 为 11.8%。',
    chart_type: 'bar',
    row_count: 2,
    execution_time_ms: 102,
    tags: ['昊铂', '对比'],
  },
  {
    id: 'demo-6',
    query: 'Q1 各月交付量走势',
    timestamp: '2026-09-13 09:30',
    brand: '全部',
    success: false,
    sql: undefined,
    insight: '查询失败：日期范围过大，已自动缩窄至 2025 Q1。',
    chart_type: 'line',
    row_count: 0,
    execution_time_ms: 0,
  },
];

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [filter, setFilter] = useState<'all' | 'success' | 'failed'>('all');
  const [search, setSearch] = useState('');
  const [detail, setDetail] = useState<HistoryItem | null>(null);
  const [editing, setEditing] = useState<HistoryItem | null>(null);
  const [toast, setToast] = useState<{ type: 'ok' | 'err'; msg: string } | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        setItems(JSON.parse(raw));
      } else {
        // 首次进入：灌入 demo 数据（演示用）
        const demo = seedDemoData();
        setItems(demo);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(demo));
      }
    } catch {
      // ignore
    }
  }, []);

  function showToast(type: 'ok' | 'err', msg: string) {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 2200);
  }

  function persist(next: HistoryItem[]) {
    setItems(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore
    }
  }

  function handleDelete(id: string) {
    if (!confirm('确定删除这条历史会话吗？此操作不可恢复。')) return;
    persist(items.filter((i) => i.id !== id));
    showToast('ok', '已删除');
  }

  function handleReExecute(item: HistoryItem) {
    if (typeof window !== 'undefined') {
      localStorage.setItem('gac-pending-query', item.query);
      window.location.href = '/';
    }
  }

  function handleSaveEdit() {
    if (!editing) return;
    persist(items.map((i) => (i.id === editing.id ? editing : i)));
    setEditing(null);
    showToast('ok', '已保存修改');
  }

  function handleExportOne(item: HistoryItem) {
    const md = generateMarkdownReport(item);
    downloadFile(`${item.id}.md`, md, 'text/markdown');
    showToast('ok', `已导出 ${item.id}.md`);
  }

  function handleExportAll() {
    const md = `# 历史会话分析报告

> 导出时间：${new Date().toLocaleString('zh-CN')}
> 会话数量：${items.length}

${items.map((i) => generateMarkdownReport(i)).join('\n\n---\n\n')}
`;
    downloadFile(`gac-chatbi-history-${Date.now()}.md`, md, 'text/markdown');
    showToast('ok', `已导出全部 ${items.length} 条会话`);
  }

  function handleClearAll() {
    if (!confirm(`确定清空全部 ${items.length} 条历史会话吗？此操作不可恢复。`)) return;
    persist([]);
    showToast('ok', '已清空');
  }

  const filtered = items
    .filter((i) => (filter === 'all' ? true : filter === 'success' ? i.success : !i.success))
    .filter((i) => (search.trim() ? i.query.toLowerCase().includes(search.toLowerCase()) : true));

  const successCount = items.filter((i) => i.success).length;
  const failCount = items.length - successCount;

  return (
    <div className="content-wrap">
      {/* Header */}
      <div className="content-card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0"><GacBadge size="lg" /></div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gac-gray-900 mb-1">历史会话</h2>
            <p className="text-sm text-gac-gray-500 leading-relaxed">
              您最近的查询记录，支持查看详情、编辑备注、重新执行、删除单条、批量导出分析报告。
              <span className="text-gac-primary font-medium ml-2">
                共 {items.length} 条（✅ {successCount} · ❌ {failCount}）
              </span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportAll}
              disabled={items.length === 0}
              className="px-3 py-1.5 text-xs bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg transition-colors disabled:opacity-50"
            >
              📥 导出全部
            </button>
            <button
              onClick={handleClearAll}
              disabled={items.length === 0}
              className="px-3 py-1.5 text-xs bg-red-50 text-red-600 hover:bg-red-100 rounded-lg transition-colors disabled:opacity-50"
            >
              🗑 清空
            </button>
          </div>
        </div>
      </div>

      {/* 筛选 + 搜索 */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="flex items-center gap-2">
          {(['all', 'success', 'failed'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={filter === f ? 'btn-primary' : 'btn-secondary'}
            >
              {f === 'all' ? `全部 (${items.length})` : f === 'success' ? `✅ 成功 (${successCount})` : `❌ 失败 (${failCount})`}
            </button>
          ))}
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="🔍 搜索问题关键词..."
          className="flex-1 min-w-[200px] px-3 py-1.5 text-sm border border-gac-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gac-primary"
        />
      </div>

      {/* 列表 */}
      <div className="content-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gac-gray-50 border-b border-gac-gray-200">
            <tr>
              <th className="px-5 py-3 text-left font-semibold text-gac-gray-700">问题</th>
              <th className="px-5 py-3 text-left font-semibold text-gac-gray-700">品牌</th>
              <th className="px-5 py-3 text-left font-semibold text-gac-gray-700">时间</th>
              <th className="px-5 py-3 text-left font-semibold text-gac-gray-700">状态</th>
              <th className="px-5 py-3 text-right font-semibold text-gac-gray-700">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id} className="border-b border-gac-gray-100 hover:bg-gac-gray-50">
                <td className="px-5 py-4 text-gac-gray-900 max-w-md">
                  <div className="truncate font-medium">{item.query}</div>
                  {item.tags && item.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {item.tags.map((t) => (
                        <span key={t} className="text-[10px] px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded">
                          #{t}
                        </span>
                      ))}
                    </div>
                  )}
                  {item.note && (
                    <div className="text-xs text-gac-gray-500 mt-1 truncate">📝 {item.note}</div>
                  )}
                </td>
                <td className="px-5 py-4">
                  <span className="text-xs px-2 py-1 bg-blue-50 text-gac-primary rounded">
                    {item.brand}
                  </span>
                </td>
                <td className="px-5 py-4 text-gac-gray-500 text-xs font-mono">{item.timestamp}</td>
                <td className="px-5 py-4">
                  {item.success ? (
                    <span className="text-xs text-emerald-600 font-medium">✅ 成功</span>
                  ) : (
                    <span className="text-xs text-red-500 font-medium">❌ 失败</span>
                  )}
                  {item.row_count !== undefined && item.row_count > 0 && (
                    <div className="text-[10px] text-gac-gray-400 mt-0.5">{item.row_count} 行</div>
                  )}
                </td>
                <td className="px-5 py-4 text-right">
                  <div className="inline-flex items-center gap-1.5 text-xs">
                    <button
                      onClick={() => setDetail(item)}
                      className="px-2 py-1 text-blue-700 hover:bg-blue-50 rounded transition-colors"
                    >
                      📋 详情
                    </button>
                    <button
                      onClick={() => setEditing({ ...item })}
                      className="px-2 py-1 text-amber-700 hover:bg-amber-50 rounded transition-colors"
                    >
                      ✏️ 编辑
                    </button>
                    <button
                      onClick={() => handleReExecute(item)}
                      className="px-2 py-1 text-gac-primary hover:bg-blue-50 rounded transition-colors"
                    >
                      ▶ 重跑
                    </button>
                    <button
                      onClick={() => handleExportOne(item)}
                      className="px-2 py-1 text-emerald-700 hover:bg-emerald-50 rounded transition-colors"
                    >
                      📥 导出
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="px-2 py-1 text-red-500 hover:bg-red-50 rounded transition-colors"
                    >
                      🗑 删除
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-gac-gray-500">
          <div className="text-5xl mb-3">📜</div>
          <p>{items.length === 0 ? '暂无历史记录' : '没有匹配的记录'}</p>
        </div>
      )}

      {/* 详情 Modal */}
      {detail && <DetailModal item={detail} onClose={() => setDetail(null)} />}

      {/* 编辑 Modal */}
      {editing && (
        <EditModal
          data={editing}
          onChange={setEditing}
          onClose={() => setEditing(null)}
          onSave={handleSaveEdit}
        />
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

// ============================================================
// 子组件：详情 Modal
// ============================================================
function DetailModal({ item, onClose }: { item: HistoryItem; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-gac-gray-200 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-gac-gray-900">📋 会话详情</h3>
            <p className="text-xs text-gac-gray-500 mt-1">{item.timestamp} · {item.brand}</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gac-gray-100 text-gac-gray-500"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6 space-y-4">
          {/* 问题 */}
          <div>
            <div className="text-xs text-gac-gray-500 mb-1">❓ 用户问题</div>
            <div className="px-3 py-2 bg-blue-50 text-gac-gray-900 rounded-lg text-sm">
              {item.query}
            </div>
          </div>

          {/* 状态指标 */}
          <div className="grid grid-cols-4 gap-3">
            <Metric label="状态" value={item.success ? '✅ 成功' : '❌ 失败'} />
            <Metric label="行数" value={item.row_count?.toString() ?? '—'} />
            <Metric label="耗时" value={item.execution_time_ms ? `${item.execution_time_ms} ms` : '—'} />
            <Metric label="图表" value={item.chart_type ?? '—'} />
          </div>

          {/* SQL */}
          {item.sql && (
            <div>
              <div className="text-xs text-gac-gray-500 mb-1">🔧 执行的 SQL</div>
              <pre className="px-3 py-2 bg-gac-gray-900 text-emerald-300 rounded-lg text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                {item.sql}
              </pre>
            </div>
          )}

          {/* 经营洞察 */}
          {item.insight && (
            <div>
              <div className="text-xs text-gac-gray-500 mb-1">💡 经营洞察</div>
              <div className="px-3 py-2 bg-amber-50 text-gac-gray-900 rounded-lg text-sm whitespace-pre-wrap">
                {item.insight}
              </div>
            </div>
          )}

          {/* 标签 + 备注 */}
          {((item.tags && item.tags.length > 0) || item.note) && (
            <div>
              <div className="text-xs text-gac-gray-500 mb-1">🏷️ 标签 & 备注</div>
              <div className="px-3 py-2 bg-gac-gray-50 rounded-lg text-sm">
                {item.tags && item.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {item.tags.map((t) => (
                      <span key={t} className="text-xs px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                        #{t}
                      </span>
                    ))}
                  </div>
                )}
                {item.note && <div className="text-gac-gray-700">📝 {item.note}</div>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-3 py-2 bg-gac-gray-50 rounded-lg">
      <div className="text-xs text-gac-gray-500">{label}</div>
      <div className="text-sm font-semibold text-gac-gray-900 mt-0.5">{value}</div>
    </div>
  );
}

// ============================================================
// 子组件：编辑 Modal
// ============================================================
function EditModal({
  data,
  onChange,
  onClose,
  onSave,
}: {
  data: HistoryItem;
  onChange: (d: HistoryItem) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  const [tagInput, setTagInput] = useState('');

  function addTag() {
    if (!tagInput.trim()) return;
    const next = Array.from(new Set([...(data.tags ?? []), tagInput.trim()]));
    onChange({ ...data, tags: next });
    setTagInput('');
  }

  function removeTag(t: string) {
    onChange({ ...data, tags: (data.tags ?? []).filter((x) => x !== t) });
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-gac-gray-200 flex items-center justify-between">
          <h3 className="text-base font-semibold text-gac-gray-900">✏️ 编辑会话</h3>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gac-gray-100 text-gac-gray-500"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs text-gac-gray-600 mb-1">问题（不可修改，如需变更请重跑）</label>
            <div className="px-3 py-2 bg-gac-gray-50 rounded-lg text-sm text-gac-gray-700">
              {data.query}
            </div>
          </div>

          <div>
            <label className="block text-xs text-gac-gray-600 mb-1">备注（私人笔记，最多 200 字）</label>
            <textarea
              value={data.note ?? ''}
              onChange={(e) => onChange({ ...data, note: e.target.value.slice(0, 200) })}
              placeholder="例：高管关注的指标 / 下次复盘备注 / 口径来源..."
              rows={3}
              className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
            />
            <div className="text-xs text-gac-gray-400 mt-1 text-right">
              {(data.note ?? '').length} / 200
            </div>
          </div>

          <div>
            <label className="block text-xs text-gac-gray-600 mb-1">标签（用于分类检索）</label>
            <div className="flex flex-wrap gap-1 mb-2">
              {(data.tags ?? []).map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded"
                >
                  #{t}
                  <button onClick={() => removeTag(t)} className="hover:text-red-500">✕</button>
                </span>
              ))}
              {(data.tags ?? []).length === 0 && (
                <span className="text-xs text-gac-gray-400">暂无标签</span>
              )}
            </div>
            <div className="flex gap-2">
              <input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                placeholder="输入标签后回车添加"
                maxLength={20}
                className="flex-1 px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                onClick={addTag}
                className="px-3 py-2 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg text-sm transition-colors"
              >
                + 添加
              </button>
            </div>
          </div>
        </div>

        <div className="px-6 py-3 border-t border-gac-gray-200 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gac-gray-700 hover:bg-gac-gray-100 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={onSave}
            className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition-colors"
          >
            💾 保存
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// 工具函数
// ============================================================
function generateMarkdownReport(item: HistoryItem): string {
  return `## ${item.query}

- **时间**：${item.timestamp}
- **品牌**：${item.brand}
- **状态**：${item.success ? '✅ 成功' : '❌ 失败'}${item.row_count !== undefined ? `（${item.row_count} 行）` : ''}
- **耗时**：${item.execution_time_ms ? `${item.execution_time_ms} ms` : '—'}
- **图表**：${item.chart_type ?? '—'}
${item.tags && item.tags.length > 0 ? `- **标签**：${item.tags.map((t) => `#${t}`).join(' ')}` : ''}
${item.note ? `- **备注**：${item.note}` : ''}

${item.sql ? `### SQL\n\n\`\`\`sql\n${item.sql}\n\`\`\`\n` : ''}
${item.insight ? `### 经营洞察\n\n${item.insight}\n` : ''}
`;
}

function downloadFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
