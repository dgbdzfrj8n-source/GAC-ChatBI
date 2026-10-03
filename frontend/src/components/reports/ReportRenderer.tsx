'use client';

/**
 * 报表中心 6 详情页共用的渲染器 (Sprint 8)
 *
 * 设计原则：
 * 1. 4 段式视觉：浅色 banner → 暗色 KPI → 暗色图表 → 浅色预警
 *    形成"沙漏"节奏，避免从列表浅色到 dashboard 暗色的视觉突兀。
 * 2. 数据唯一来源：GET /api/reports/{report_id}?month=YYYY-MM
 *    任何 2 张报表不复用同一个端点。
 * 3. 失败降级：接口失败 → 使用前端硬编码的极简 Mock（仅占位 1 KPI）。
 * 4. 客户端动态：所有 ECharts 必须通过 dynamic(..., { ssr: false }) 引入。
 * 5. 类型严格：完全对齐 backend/api/schemas.py 的 ReportPayload 模型。
 */

import { useEffect, useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Download, Bell, ArrowUp, ArrowDown, Minus, AlertCircle, AlertTriangle, Info, RefreshCw, ArrowLeft, Database } from 'lucide-react';
import type { ReportMeta } from '@/lib/reportRegistry';

// 通用图表渲染器（内部按 chart_type 切换 ECharts 配置，9 合 1）
const ReportChartView = dynamic(() => import('@/components/reports/ReportChartView'), { ssr: false });

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'https://gac-chatbi-api.onrender.com';

// ── 类型对齐 backend/api/schemas.py ─────────────────────────────
interface ReportKpi {
  label: string;
  value: number | string;
  unit: string;
  trend?: 'up' | 'down' | 'flat' | null;
  hint?: string | null;
}

interface ReportChart {
  chart_type:
    | 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap'
    | 'funnel' | 'waterfall' | 'table' | 'ranking';
  title: string;
  data: Array<Record<string, any>>;
  columns: string[];
  x_axis?: string | null;
  y_axis?: string | null;
  series?: string[] | null;
}

interface ReportAlert {
  level: 'info' | 'warning' | 'alert';
  title: string;
  body: string;
  link?: string | null;
}

interface ReportPayload {
  report_id: string;
  title: string;
  subtitle: string;
  month: string;
  generated_at: string;
  is_mocked: boolean;
  kpis: ReportKpi[];
  charts: ReportChart[];
  alerts: ReportAlert[];
  // ⭐ Sprint 8 增强：snapshot-driven 报表的后端返回字段
  snapshot_date?: string | null;
}

// 注：ReportMeta 已在 @/lib/reportRegistry 定义并 import 上来。

interface Props {
  reportMeta: ReportMeta;
  defaultMonth?: string;
}

// ── 图表分发表：按 chart_type 选组件 ───────────────────────────
function ChartDispatcher({ chart }: { chart: ReportChart }) {
  return <ReportChartView chart={chart} />;
}

// ── KPI 卡片 ──────────────────────────────────────────────────
function KpiCard({ kpi }: { kpi: ReportKpi }) {
  const trendIcon =
    kpi.trend === 'up' ? <ArrowUp className="w-3.5 h-3.5" /> :
    kpi.trend === 'down' ? <ArrowDown className="w-3.5 h-3.5" /> :
    kpi.trend === 'flat' ? <Minus className="w-3.5 h-3.5" /> :
    null;
  const trendColor =
    kpi.trend === 'up' ? 'text-emerald-400' :
    kpi.trend === 'down' ? 'text-rose-400' :
    kpi.trend === 'flat' ? 'text-gac-gray-400' :
    'text-gac-gray-500';

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
      <div className="text-xs text-slate-400 mb-1">{kpi.label}</div>
      <div className="flex items-baseline gap-1.5">
        <div className="text-2xl font-bold text-white">{kpi.value}</div>
        {kpi.unit && <div className="text-sm text-slate-400">{kpi.unit}</div>}
        {trendIcon && <div className={`ml-1 ${trendColor}`}>{trendIcon}</div>}
      </div>
      {kpi.hint && (
        <div className="text-[11px] text-slate-500 mt-1">{kpi.hint}</div>
      )}
    </div>
  );
}

// ── 告警图标 ──────────────────────────────────────────────────
function AlertIcon({ level }: { level: ReportAlert['level'] }) {
  if (level === 'alert') return <AlertCircle className="w-5 h-5 text-rose-500" />;
  if (level === 'warning') return <AlertTriangle className="w-5 h-5 text-amber-500" />;
  return <Info className="w-5 h-5 text-sky-500" />;
}

// ── 主组件 ──────────────────────────────────────────────────
export default function ReportRenderer({ reportMeta, defaultMonth = '2025-03' }: Props) {
  const [payload, setPayload] = useState<ReportPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [month, setMonth] = useState(defaultMonth);

  // 月份可选范围：2024-04 ~ 2025-04
  const monthOptions = useMemo(() => {
    const months: string[] = [];
    for (let y = 2024; y <= 2025; y++) {
      for (let m = 1; m <= 12; m++) {
        if (y === 2024 && m < 4) continue;
        if (y === 2025 && m > 4) continue;
        months.push(`${y}-${String(m).padStart(2, '0')}`);
      }
    }
    return months;
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`${API_URL}/api/reports/${reportMeta.report_id}?month=${month}`, {
      cache: 'no-store',
    })
      .then(async (r) => {
        if (!r.ok) {
          const text = await r.text();
          throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
        }
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        setPayload(data);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.warn(`[ReportRenderer] ${reportMeta.report_id} 加载失败:`, err);
        setError(err.message || '数据加载失败');
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, [reportMeta.report_id, month]);

  const onRetry = () => {
    setLoading(true);
    setError(null);
    // 触发 effect 重跑
    setMonth((m) => m);
    setTimeout(() => {
      // 强制重 fetch
      fetch(`${API_URL}/api/reports/${reportMeta.report_id}?month=${month}`, { cache: 'no-store' })
        .then((r) => r.json())
        .then((data) => { setPayload(data); setLoading(false); })
        .catch((err) => { setError(err.message); setLoading(false); });
    }, 50);
  };

  return (
    <div>
      {/* ── Section 1: 浅色 banner（与 /reports 列表同色系）── */}
      <div className="content-wrap">
        <div className="content-card p-5 mb-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex-1 min-w-[240px]">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-2xl">{reportMeta.icon}</span>
                <h2 className="text-base font-semibold text-gac-gray-900">
                  {reportMeta.name}
                </h2>
                <span className="text-xs px-2 py-1 bg-blue-50 text-gac-primary rounded">
                  {reportMeta.category}
                </span>
                {payload?.is_mocked && (
                  <span className="text-xs px-2 py-1 bg-amber-50 text-amber-700 rounded border border-amber-200">
                    📦 演示数据
                  </span>
                )}
              </div>
              <p className="text-sm text-gac-gray-500 leading-relaxed">
                {reportMeta.description}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {/* 条件渲染：snapshot-driven 报表隐藏月份选择器，显示快照日徽章 */}
              {reportMeta.snapshotDriven ? (
                <div
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-sky-200 bg-sky-50 text-sky-700 text-sm"
                  title="该报表由最新库存快照日驱动，无法回放历史"
                >
                  <Database className="w-4 h-4" />
                  <span className="font-medium">快照日</span>
                  <span className="font-mono">
                    {payload?.snapshot_date || '加载中…'}
                  </span>
                </div>
              ) : (
                <select
                  value={month}
                  onChange={(e) => setMonth(e.target.value)}
                  className="px-3 py-2 rounded-lg border border-gac-gray-200 text-sm text-gac-gray-700 bg-white hover:border-gac-primary"
                >
                  {monthOptions.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              )}
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
                className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-gac-gray-200 text-sm text-gac-gray-700 hover:bg-gac-gray-100"
              >
                <ArrowLeft className="w-4 h-4" />
                返回
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* ── 加载态 ── */}
      {loading && (
        <div className="content-wrap">
          <div className="content-card p-12 text-center">
            <RefreshCw className="w-8 h-8 text-gac-primary animate-spin mx-auto mb-3" />
            <div className="text-sm text-gac-gray-500">正在加载 {reportMeta.name} 数据...</div>
          </div>
        </div>
      )}

      {/* ── 错误态 ── */}
      {error && !loading && !payload && (
        <div className="content-wrap">
          <div className="content-card p-6 border-rose-200 bg-rose-50">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-rose-900 mb-1">数据加载失败</h3>
                <p className="text-xs text-rose-700 mb-3">{error}</p>
                <button
                  onClick={onRetry}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600 text-white text-xs hover:bg-rose-700"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  重试
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 成功态 ── */}
      {payload && !loading && (
        <>
          {/* Section 2: 暗色 KPI 行（与 dashboard 同款色） */}
          <div className="bg-slate-900 border-y border-slate-800">
            <div className="content-wrap py-5">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {payload.kpis.slice(0, 4).map((kpi, i) => (
                  <KpiCard key={i} kpi={kpi} />
                ))}
              </div>
            </div>
          </div>

          {/* Section 3: 暗色图表区 */}
          <div className="bg-slate-900">
            <div className="content-wrap py-6 space-y-4">
              {payload.charts.map((chart, i) => (
                <div
                  key={i}
                  className="bg-slate-800/60 border border-slate-700 rounded-xl p-5"
                >
                  <ChartDispatcher chart={chart} />
                </div>
              ))}
            </div>
          </div>

          {/* Section 4: 浅色告警 + 行动建议 */}
          {payload.alerts.length > 0 && (
            <div className="content-wrap py-6">
              <div className="content-card p-5">
                <h3 className="text-sm font-semibold text-gac-gray-900 mb-3">
                  ⚡ 关键预警（{payload.alerts.length}）
                </h3>
                <div className="space-y-2">
                  {payload.alerts.map((alert, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 p-3 rounded-lg border border-gac-gray-100 hover:bg-gac-gray-50"
                    >
                      <AlertIcon level={alert.level} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gac-gray-900">
                          {alert.title}
                        </div>
                        <div className="text-xs text-gac-gray-500 mt-0.5">
                          {alert.body}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 元信息 footer */}
          <div className="content-wrap pb-8">
            <div className="text-center text-xs text-gac-gray-400">
              数据生成时间：{payload.generated_at}
              {reportMeta.snapshotDriven && payload.snapshot_date
                ? ` · 快照日：${payload.snapshot_date}`
                : ` · 月份：${payload.month}`}
              {payload.is_mocked && ' · 演示数据'}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
