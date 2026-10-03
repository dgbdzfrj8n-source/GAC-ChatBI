'use client';

/**
 * 通用图表渲染器 (Sprint 8 报表中心)
 * - 内部按 chart.chart_type 切换 ECharts 配置；
 * - 所有 9 种类型集中在一个文件，避免组件爆炸；
 * - 暗色主题，与 ReportRenderer 暗色 section 配套；
 * - ECharts 走客户端 dynamic(..., { ssr: false })，避免 SSR 水合冲突。
 */

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';

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

const COLORS = ['#fbbf24', '#34d399', '#60a5fa', '#a78bfa', '#f87171', '#fb923c'];

const BASE_AXIS = {
  axisLine: { lineStyle: { color: '#475569' } },
  axisLabel: { color: '#94a3b8', fontSize: 11 },
};
const BASE_TOOLTIP: any = {
  trigger: 'axis',
  backgroundColor: 'rgba(15, 23, 42, 0.95)',
  borderColor: '#475569',
  textStyle: { color: '#fff' },
};

function getBarOption(chart: ReportChart): EChartsOption {
  const xKey = chart.x_axis || chart.columns[0];
  const yKey = chart.y_axis || chart.columns[1];
  return {
    backgroundColor: 'transparent',
    tooltip: BASE_TOOLTIP,
    grid: { left: 60, right: 30, top: 30, bottom: 50 },
    xAxis: { ...BASE_AXIS, type: 'category', data: chart.data.map((d) => String(d[xKey] ?? '')) },
    yAxis: { ...BASE_AXIS, type: 'value' },
    color: COLORS,
    series: [{
      name: yKey,
      type: 'bar',
      data: chart.data.map((d) => Number(d[yKey] ?? 0)),
      itemStyle: { borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', color: '#cbd5e1', fontSize: 10 },
    }],
  };
}

function getLineOption(chart: ReportChart): EChartsOption {
  const xKey = chart.x_axis || chart.columns[0];
  const series = chart.series && chart.series.length
    ? chart.series
    : chart.columns.slice(1);
  return {
    backgroundColor: 'transparent',
    tooltip: BASE_TOOLTIP,
    legend: { data: series, textStyle: { color: '#cbd5e1' }, top: 0, right: 0 },
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
    xAxis: { ...BASE_AXIS, type: 'category', data: chart.data.map((d) => String(d[xKey] ?? '')) },
    yAxis: { ...BASE_AXIS, type: 'value' },
    color: COLORS,
    series: series.map((s) => ({
      name: s,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2.5 },
      data: chart.data.map((d) => Number(d[s] ?? 0)),
    })),
  };
}

function getPieOption(chart: ReportChart): EChartsOption {
  const nameKey = chart.columns[0];
  const valueKey = chart.columns[1];
  return {
    backgroundColor: 'transparent',
    tooltip: { ...BASE_TOOLTIP, trigger: 'item' },
    legend: { textStyle: { color: '#cbd5e1' }, bottom: 0 },
    color: COLORS,
    series: [{
      name: chart.title,
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      data: chart.data.map((d) => ({ name: String(d[nameKey] ?? ''), value: Number(d[valueKey] ?? 0) })),
      label: { color: '#cbd5e1', fontSize: 11 },
    }],
  };
}

function getScatterOption(chart: ReportChart): EChartsOption {
  const xKey = chart.x_axis || chart.columns[0];
  const yKey = chart.y_axis || chart.columns[1];
  const sizeKey = chart.columns[3] || chart.columns[2];
  return {
    backgroundColor: 'transparent',
    tooltip: {
      ...BASE_TOOLTIP,
      formatter: (p: any) =>
        `${p.data.name}<br/>${xKey}: ${p.data.value[0]}<br/>${yKey}: ${p.data.value[1]}<br/>${sizeKey}: ${p.data.value[2]}`,
    },
    grid: { left: 60, right: 30, top: 30, bottom: 50 },
    xAxis: { ...BASE_AXIS, type: 'value', name: xKey },
    yAxis: { ...BASE_AXIS, type: 'value', name: yKey },
    color: COLORS,
    series: [{
      type: 'scatter',
      data: chart.data.map((d) => ({
        name: d[chart.columns[0]],
        value: [Number(d[xKey] ?? 0), Number(d[yKey] ?? 0), Number(d[sizeKey] ?? 0)],
      })),
      symbolSize: (val: any[]) => Math.max(8, Math.min(40, val[2] * 2)),
      itemStyle: { opacity: 0.7 },
    }],
  };
}

function getHeatmapOption(chart: ReportChart): EChartsOption {
  // columns[0] = 行名（如车型），其余为列名（如大区）
  const rowKey = chart.columns[0];
  const colKeys = chart.columns.slice(1);
  const data: [number, number, number][] = [];
  chart.data.forEach((row, i) => {
    colKeys.forEach((c, j) => {
      const v = Number(row[c] ?? 0);
      data.push([j, i, v]);
    });
  });
  return {
    backgroundColor: 'transparent',
    tooltip: {
      ...BASE_TOOLTIP,
      formatter: (p: any) =>
        `${chart.data[p.value[1]][rowKey]} / ${colKeys[p.value[0]]}<br/>${p.value[2]}`,
    },
    grid: { left: 80, right: 30, top: 20, bottom: 60 },
    xAxis: { ...BASE_AXIS, type: 'category', data: colKeys, splitArea: { show: true } },
    yAxis: { ...BASE_AXIS, type: 'category', data: chart.data.map((d) => String(d[rowKey] ?? '')), splitArea: { show: true } },
    visualMap: {
      min: 0,
      max: 3,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#10b981', '#fbbf24', '#f87171'] },
      textStyle: { color: '#cbd5e1', fontSize: 10 },
    },
    series: [{
      name: chart.title,
      type: 'heatmap',
      data,
      label: { show: true, color: '#0f172a', fontSize: 10 },
    }],
  };
}

function getFunnelOption(chart: ReportChart): EChartsOption {
  const nameKey = chart.columns[0];
  const valueKey = chart.columns[1];
  return {
    backgroundColor: 'transparent',
    tooltip: { ...BASE_TOOLTIP, trigger: 'item' },
    legend: { textStyle: { color: '#cbd5e1' }, bottom: 0 },
    color: COLORS,
    series: [{
      name: chart.title,
      type: 'funnel',
      left: '10%', top: 20, bottom: 20, width: '80%',
      sort: 'descending',
      gap: 2,
      label: { show: true, position: 'inside', color: '#0f172a', fontWeight: 'bold' },
      data: chart.data.map((d) => ({ name: String(d[nameKey] ?? ''), value: Number(d[valueKey] ?? 0) })),
    }],
  };
}

function getWaterfallOption(chart: ReportChart): EChartsOption {
  const xKey = chart.x_axis || chart.columns[0];
  const yKey = chart.y_axis || chart.columns[1];
  // 辅助栈：上涨 / 下跌 / 合计
  const data = chart.data;
  const helper: number[] = [];
  const positives: number[] = [];
  const totals: number[] = [];
  let running = 0;
  data.forEach((d, i) => {
    const y = Number(d[yKey] ?? 0);
    const label = String(d[xKey] ?? '');
    const isLast = label.includes('合计') || i === data.length - 1;
    if (isLast) {
      totals.push(y);
      positives.push(0);
      helper.push(0);
    } else if (y >= 0) {
      positives.push(y);
      helper.push(running);
      running += y;
      totals.push(0);
    } else {
      positives.push(0);
      running += y;
      helper.push(running);
      totals.push(0);
    }
  });
  return {
    backgroundColor: 'transparent',
    tooltip: { ...BASE_TOOLTIP, trigger: 'axis' },
    grid: { left: 60, right: 30, top: 30, bottom: 50 },
    xAxis: { ...BASE_AXIS, type: 'category', data: data.map((d) => String(d[xKey] ?? '')) },
    yAxis: { ...BASE_AXIS, type: 'value' },
    color: COLORS,
    series: [
      { name: 'placeholder', type: 'bar', stack: 'total', itemStyle: { color: 'transparent' }, data: helper },
      { name: '贡献', type: 'bar', stack: 'total', data: positives, itemStyle: { color: '#34d399' } },
      { name: '合计', type: 'bar', stack: 'total', data: totals, itemStyle: { color: '#fbbf24' } },
    ],
  };
}

function getOption(chart: ReportChart): EChartsOption | null {
  switch (chart.chart_type) {
    case 'bar': return getBarOption(chart);
    case 'line': return getLineOption(chart);
    case 'pie': return getPieOption(chart);
    case 'scatter': return getScatterOption(chart);
    case 'heatmap': return getHeatmapOption(chart);
    case 'funnel': return getFunnelOption(chart);
    case 'waterfall': return getWaterfallOption(chart);
    default: return null;
  }
}

// ── 非 ECharts 类型：table / ranking ─────────────────────────
function TableView({ chart }: { chart: ReportChart }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700">
            {chart.columns.map((c) => (
              <th key={c} className="text-left py-2 px-3 text-slate-300 font-medium text-xs">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {chart.data.map((row, i) => (
            <tr key={i} className="border-b border-slate-800 hover:bg-slate-700/30">
              {chart.columns.map((c) => (
                <td key={c} className="py-2 px-3 text-slate-200">
                  {String(row[c] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RankingView({ chart }: { chart: ReportChart }) {
  const valueKey = chart.y_axis || chart.columns[1] || 'value';
  const labelKey = chart.columns[0] || 'name';
  const max = Math.max(...chart.data.map((d) => Number(d[valueKey] ?? 0)), 1);
  return (
    <div className="space-y-2">
      {chart.data.map((d, i) => {
        const v = Number(d[valueKey] ?? 0);
        const pct = (v / max) * 100;
        return (
          <div key={i} className="flex items-center gap-3">
            <div className="w-32 truncate text-sm text-slate-200">{String(d[labelKey] ?? '')}</div>
            <div className="flex-1 h-6 bg-slate-800 rounded overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-amber-500 to-amber-300"
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="w-20 text-right text-sm text-slate-300 font-mono">
              {v.toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── 主组件 ──────────────────────────────────────────────────
interface Props {
  chart: ReportChart;
}

export default function ReportChartView({ chart }: Props) {
  // table / ranking 不需要 ECharts
  if (chart.chart_type === 'table') {
    return (
      <div>
        <ChartTitle title={chart.title} />
        <TableView chart={chart} />
      </div>
    );
  }
  if (chart.chart_type === 'ranking') {
    return (
      <div>
        <ChartTitle title={chart.title} />
        <RankingView chart={chart} />
      </div>
    );
  }

  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const opt = getOption(chart);
    if (opt) {
      chartInstance.current.setOption(opt, true);
    }
    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [chart]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return (
    <div>
      <ChartTitle title={chart.title} />
      <div ref={chartRef} style={{ width: '100%', height: '360px' }} />
    </div>
  );
}

function ChartTitle({ title }: { title: string }) {
  return (
    <h3 className="text-sm font-semibold text-slate-200 mb-3">{title}</h3>
  );
}
