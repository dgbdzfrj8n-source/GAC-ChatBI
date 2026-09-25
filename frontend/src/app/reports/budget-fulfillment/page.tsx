'use client';

// 预算达成分析报表
// 视图复用驾驶舱 SnapshotBoard：4 KPI（综合达成率 / 总交付量 / 总营收 / 平均 CPL）+ 趋势 + 品牌达成率排名 + 预警。
// 后续可在此处叠加"预算 vs 实际"对比维度。

import Link from 'next/link';
import { Download, Bell } from 'lucide-react';
import SnapshotBoard from '@/components/reports/SnapshotBoard';

export default function BudgetFulfillmentReportPage() {
  return (
    <>
      {/* 报表头部说明（浅色风格，与暗色仪表板形成过渡） */}
      <div className="content-wrap">
        <div className="content-card p-5 mb-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex-1 min-w-[240px]">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-2xl">📊</span>
                <h2 className="text-base font-semibold text-gac-gray-900">预算达成分析</h2>
                <span className="text-xs px-2 py-1 bg-blue-50 text-gac-primary rounded">整车销售</span>
              </div>
              <p className="text-sm text-gac-gray-500 leading-relaxed">
                各品牌、各大区、各车型的预算完成进度，自动识别达成率低于 90% 的薄弱项。
                下方视图为复用驾驶舱核心指标，导出与订阅为占位按钮，后续迭代。
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
        title="预算达成分析 · 驾驶舱视图"
        subtitle="Sprint 7 实现 · 导出 / 订阅功能后续迭代"
      />
    </>
  );
}
