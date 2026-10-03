'use client';

// 报表中心列表页 (Sprint 8)
// 数据源：frontend/src/lib/reportRegistry.ts（中央注册表，与后端 /api/reports/registry 对齐）

import Link from 'next/link';
import { useState, useEffect } from 'react';
import GacBadge from '@/components/GacBadge';
import { REPORT_REGISTRY, type ReportMeta } from '@/lib/reportRegistry';

const CATEGORIES = ['全部', '整车销售', '经营财务', '市场营销', '渠道经营', '库存管理'];

const STATUS_BADGE: Record<ReportMeta['status'], { text: string; className: string }> = {
  ready: {
    text: '✅ 已就绪',
    className: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  },
  mocked: {
    text: '📦 演示数据',
    className: 'bg-amber-50 text-amber-700 border border-amber-200',
  },
  wip: {
    text: '🚧 开发中',
    className: 'bg-slate-100 text-slate-600 border border-slate-200',
  },
};

export default function ReportsPage() {
  const [activeCategory, setActiveCategory] = useState('全部');
  const [serverRegistry, setServerRegistry] = useState<ReportMeta[]>([]);

  // 拉后端 registry 拿真实 status（降级时不影响渲染）
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://gac-chatbi-api.onrender.com';
    fetch(`${apiUrl}/api/reports/registry`, { cache: 'no-store' })
      .then((r) => r.json())
      .then((data) => {
        if (data?.items && Array.isArray(data.items)) {
          setServerRegistry(data.items as ReportMeta[]);
        }
      })
      .catch(() => {
        // 静默失败，保留前端兜底
      });
  }, []);

  // 优先用后端 registry 覆盖前端常量
  const reports: ReportMeta[] = Object.values(REPORT_REGISTRY).map((local) => {
    const server = serverRegistry.find((s) => s.report_id === local.report_id);
    return server ? { ...local, status: server.status, description: server.description || local.description } : local;
  });

  const filtered = activeCategory === '全部'
    ? reports
    : reports.filter((r) => r.category === activeCategory);

  const readyCount = reports.filter((r) => r.status === 'ready').length;
  const mockedCount = reports.filter((r) => r.status === 'mocked').length;

  return (
    <div className="content-wrap">
      {/* 顶部说明 */}
      <div className="content-card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0"><GacBadge size="lg" /></div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gac-gray-900 mb-1">报表中心</h2>
            <p className="text-sm text-gac-gray-500 leading-relaxed">
              高频经营场景的标准报表模板，集成 SOP 归因引擎与指标口径，可一键导出与定时订阅。
              <span className="text-gac-primary font-medium ml-2">
                共 {reports.length} 个标准报表（{readyCount} 已就绪 / {mockedCount} 演示）
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* 分类筛选 */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={
              activeCategory === cat
                ? 'btn-primary'
                : 'px-4 py-2 bg-white text-gac-gray-700 border border-gac-gray-200 rounded-lg text-sm font-medium hover:bg-gac-gray-100'
            }
          >
            {cat}
          </button>
        ))}
      </div>

      {/* 报表卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((report) => {
          const badge = STATUS_BADGE[report.status] || STATUS_BADGE.ready;
          return (
            <Link
              key={report.report_id}
              href={`/reports/${report.report_id}`}
              className="content-card p-5 hover:shadow-md hover:border-gac-primary transition-all block"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="text-3xl">{report.icon}</div>
                <div className="flex flex-col items-end gap-1">
                  <span className="text-xs px-2 py-1 bg-blue-50 text-gac-primary rounded">
                    {report.category}
                  </span>
                  <span className={`text-[11px] px-2 py-0.5 rounded ${badge.className}`}>
                    {badge.text}
                  </span>
                </div>
              </div>
              <h3 className="text-base font-semibold text-gac-gray-900 mb-2">
                {report.name}
              </h3>
              <p className="text-sm text-gac-gray-500 leading-relaxed mb-4 min-h-[48px]">
                {report.description}
              </p>
              <div className="flex items-center justify-end">
                <span className="text-xs text-gac-primary font-medium">
                  查看 →
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
