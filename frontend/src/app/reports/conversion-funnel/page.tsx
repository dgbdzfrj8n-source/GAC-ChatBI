'use client';

// 客流转化漏斗报表
// 复用驾驶舱 SnapshotBoard；后续叠加"客流 → 留资 → 试驾 → 成交"四级漏斗图。

import Link from 'next/link';
import { Download, Bell } from 'lucide-react';
import SnapshotBoard from '@/components/reports/SnapshotBoard';

export default function ConversionFunnelReportPage() {
  return (
    <>
      <div className="content-wrap">
        <div className="content-card p-5 mb-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex-1 min-w-[240px]">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-2xl">🎯</span>
                <h2 className="text-base font-semibold text-gac-gray-900">客流转化漏斗</h2>
                <span className="text-xs px-2 py-1 bg-blue-50 text-gac-primary rounded">渠道经营</span>
              </div>
              <p className="text-sm text-gac-gray-500 leading-relaxed">
                从客流 → 留资 → 试驾 → 成交的全链路转化率分析，定位流失环节。
                下方视图为复用驾驶舱核心指标，四级漏斗图后续叠加。
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled
                title="导出功能后续迭代"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gac-gray-200 text-sm text-gac-gray-500 cursor-not-allowed"
              >
                <Download className="w-4 h-4" />
                导出
              </button>
              <button
                type="button"
                disabled
                title="订阅功能后续迭代"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gac-gray-200 text-sm text-gac-gray-500 cursor-not-allowed"
              >
                <Bell className="w-4 h-4" />
                订阅
              </button>
              <Link
                href="/reports"
                className="inline-flex items-center px-3 py-2 rounded-lg border border-gac-gray-200 text-sm text-gac-gray-700 hover:bg-gac-gray-100"
              >
                ← 返回报表中心
              </Link>
            </div>
          </div>
        </div>
      </div>

      <SnapshotBoard
        title="客流转化漏斗 · 驾驶舱视图"
        subtitle="Sprint 7 实现 · 四级漏斗图后续叠加"
      />
    </>
  );
}
