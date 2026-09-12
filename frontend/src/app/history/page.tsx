'use client';

import { useEffect, useState } from 'react';
import GacLogo from '@/components/GacLogo';

interface HistoryItem {
  id: string;
  query: string;
  timestamp: string;
  brand: string;
  success: boolean;
}

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [filter, setFilter] = useState<'all' | 'success' | 'failed'>('all');

  useEffect(() => {
    // 从 localStorage 读取（如果 chat 页面有存储的话）
    try {
      const raw = localStorage.getItem('gac-chatbi-history');
      if (raw) {
        setItems(JSON.parse(raw));
      }
    } catch {
      // ignore
    }
  }, []);

  // 演示数据
  const demoItems: HistoryItem[] = [
    {
      id: '1',
      query: '2025年3月埃安销量与预算达成率是多少？',
      timestamp: '2026-09-12 14:23',
      brand: '广汽埃安',
      success: true,
    },
    {
      id: '2',
      query: '各品牌总交付量与总营收是多少？',
      timestamp: '2026-09-12 14:18',
      brand: '全部',
      success: true,
    },
    {
      id: '3',
      query: '抖音渠道的 CPL 在所有渠道里排第几？',
      timestamp: '2026-09-12 14:12',
      brand: '全部',
      success: true,
    },
    {
      id: '4',
      query: '传祺 GS8 在华南大区 8 月销量',
      timestamp: '2026-09-12 13:55',
      brand: '广汽传祺',
      success: true,
    },
    {
      id: '5',
      query: '昊铂 HT 与昊铂 GT 客流转化率对比',
      timestamp: '2026-09-12 13:40',
      brand: '昊铂',
      success: true,
    },
    {
      id: '6',
      query: 'Q1 各月交付量走势',
      timestamp: '2026-09-12 11:30',
      brand: '全部',
      success: false,
    },
  ];

  const display = items.length > 0 ? items : demoItems;
  const filtered = filter === 'all'
    ? display
    : display.filter((i) => (filter === 'success' ? i.success : !i.success));

  return (
    <div className="content-wrap">
      {/* 顶部说明 */}
      <div className="content-card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0"><GacLogo size="lg" /></div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gac-gray-900 mb-1">历史会话</h2>
            <p className="text-sm text-gac-gray-500 leading-relaxed">
              您最近的查询记录，支持点击重新执行，或导出为分析报告。
              <span className="text-gac-primary font-medium ml-2">
                共 {display.length} 条记录
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* 筛选 */}
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={() => setFilter('all')}
          className={filter === 'all' ? 'btn-primary' : 'btn-secondary'}
        >
          全部
        </button>
        <button
          onClick={() => setFilter('success')}
          className={filter === 'success' ? 'btn-primary' : 'btn-secondary'}
        >
          ✅ 成功
        </button>
        <button
          onClick={() => setFilter('failed')}
          className={filter === 'failed' ? 'btn-primary' : 'btn-secondary'}
        >
          ❌ 失败
        </button>
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
                <td className="px-5 py-4 text-gac-gray-900 max-w-md truncate">
                  {item.query}
                </td>
                <td className="px-5 py-4">
                  <span className="text-xs px-2 py-1 bg-blue-50 text-gac-primary rounded">
                    {item.brand}
                  </span>
                </td>
                <td className="px-5 py-4 text-gac-gray-500 text-xs font-mono">
                  {item.timestamp}
                </td>
                <td className="px-5 py-4">
                  {item.success ? (
                    <span className="text-xs text-emerald-600 font-medium">✅ 成功</span>
                  ) : (
                    <span className="text-xs text-red-500 font-medium">❌ 失败</span>
                  )}
                </td>
                <td className="px-5 py-4 text-right">
                  <button className="text-xs text-gac-primary hover:underline mr-3">
                    重新执行
                  </button>
                  <button className="text-xs text-gac-gray-500 hover:text-gac-gray-700">
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-gac-gray-500">
          <div className="text-5xl mb-3">📜</div>
          <p>暂无历史记录</p>
        </div>
      )}
    </div>
  );
}
