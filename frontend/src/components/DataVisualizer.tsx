"use client";

import dynamic from "next/dynamic";

// 动态导入 ECharts 组件（SSR 水合保护）
const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

// [DIAG] 诊断开关：localStorage.setItem("gac_debug","1") 开启
const isDebug = () =>
  typeof window !== "undefined" && localStorage.getItem("gac_debug") === "1";

interface DataVisualizerProps {
  chartType?: string;
  echartsOption?: Record<string, unknown>;
  columns: string[];
  data: Record<string, unknown>[];
  viewMode: "chart" | "table";
}

// 格式化数值显示
// [P2 修复] 改进大数字格式化：万/亿/M 三档（基于列名判断量级）
const fmt = (val: unknown, colName?: string): string => {
  if (val === null || val === undefined) return "-";
  if (typeof val === "number") {
    // 已知是万元/亿元/百分比等列，直接显示
    const col = (colName || "").toLowerCase();
    if (col.includes("billion") || col.includes("亿元")) return val.toFixed(2) + " 亿元";
    if (col.includes("wan") || col.includes("万")) return val.toFixed(1) + " 万";
    if (col.includes("pct") || col.includes("率")) return val.toFixed(2) + "%";
    if (col.includes("roi") || col.includes("倍数")) return val.toFixed(2) + "x";
    if (col.includes("cpl") || col.includes("元/条")) return val.toFixed(1) + " 元";

    // 自动量级
    const abs = Math.abs(val);
    if (abs >= 100_000_000) return (val / 100_000_000).toFixed(2) + " 亿";   // 亿
    if (abs >= 10_000) return (val / 10_000).toFixed(2) + " 万";              // 万
    if (abs >= 1_000) return val.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
    return Number.isInteger(val) ? val.toString() : val.toFixed(2);
  }
  return String(val);
};

// 中文列名美化
const COL_LABELS: Record<string, string> = {
  brand_name: "品牌",
  model_name: "车型",
  region_name: "大区",
  province_name: "省份",
  channel_name: "渠道",
  expense_category: "费用类别",
  year_month: "月份",
  sale_date: "日期",
  delivered_units: "交付量(辆)",
  actual_units: "实际交付(辆)",
  target_units: "目标交付(辆)",
  gross_revenue: "总营收(元)",
  avg_price: "成交均价(元)",
  avg_price_yuan: "成交均价(元)",
  fulfillment_rate_pct: "达成率(%)",
  total_units: "总交付(辆)",
  total_delivered_units: "总交付(辆)",
  gross_revenue_billion_yuan: "总营收(亿元)",
  total_expense: "总支出(元)",
  total_expense_wan: "总支出(万元)",
  total_leads: "总线索(条)",
  cpl: "CPL(元/条)",
  cpl_yuan: "CPL(元/条)",
  discount_rate: "折扣率",
  customer_leads: "进店客流(组)",
  test_drives: "试驾次数(次)",
  conversion_rate: "客流转化率(%)",
  leads_generated: "线索量(条)",
  expense_amount: "支出金额(元)",
  marketing_cost_per_car: "单车营销费(元)",
  target_revenue: "营收目标(元)",
  expense_limit: "费用限额(元)",
};

const colLabel = (col: string): string => COL_LABELS[col] || col;

export default function DataVisualizer({ chartType, echartsOption, columns, data, viewMode }: DataVisualizerProps) {
  // [DIAG] 渲染时输出诊断日志（仅 gac_debug 开启）
  if (isDebug()) {
    // eslint-disable-next-line no-console
    console.log("[GAC-DIAG DataVisualizer]", {
      viewMode,
      hasEchartsOption: !!echartsOption,
      chartType,
      optionKeys: echartsOption ? Object.keys(echartsOption) : null,
      seriesCount: (echartsOption as any)?.series?.length ?? 0,
      cols: columns.length,
      rows: data.length,
    });
  }

  // 如果有预计算的 ECharts Option，优先使用
  // [P0 修复] funnel 类型走 ECharts 渲染（之前会被 fallback 到 table）
  if (viewMode === "chart" && echartsOption && chartType !== "table") {
    return (
      <>
        <ReactECharts
          option={echartsOption}
          style={{ height: "320px", width: "100%" }}
          opts={{ renderer: "canvas" }}
          notMerge={true}
          onChartReady={() =>
            isDebug() && console.log("[GAC-DIAG] ECharts onChartReady fired")
          }
          onChartFinished={() =>
            isDebug() && console.log("[GAC-DIAG] ECharts onChartFinished fired")
          }
        />
        {/* [DIAG] 调试条：仅 gac_debug 开启时显示 */}
        {isDebug() && (
          <div className="mt-2 p-2 border border-amber-300 bg-amber-50 rounded text-xs font-mono text-amber-900">
            <div>🐞 DEBUG · viewMode=<b>{viewMode}</b> · chartType=<b>{chartType}</b></div>
            <div>option keys: {echartsOption ? Object.keys(echartsOption).join(", ") : "null"}</div>
            <div>series count: {(echartsOption as any)?.series?.length ?? 0}</div>
            <div>data rows: {data.length} · cols: {columns.length}</div>
          </div>
        )}
      </>
    );
  }

  // 表格视图
  if (viewMode === "table" || !chartType || chartType === "table" || !echartsOption) {
    if (!data || data.length === 0) {
      return <p className="text-sm text-gray-400 text-center py-8">暂无数据</p>;
    }

    // [P2 修复] 单点 KPI 卡片渲染（适用于 Q08 / Q11 这种"单条数字+百分比"查询）
    if (chartType === "single_kpi" && data.length === 1) {
      const row = data[0];
      return (
        <div className="grid grid-cols-2 gap-4 py-4">
          {columns.map((col) => (
            <div key={col} className="bg-gradient-to-br from-emerald-50 to-blue-50 rounded-lg p-4 border border-emerald-100">
              <p className="text-xs text-gray-500 mb-1">{colLabel(col)}</p>
              <p className="text-2xl font-bold text-emerald-700">{fmt(row[col], col)}</p>
            </div>
          ))}
        </div>
      );
    }

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              {columns.map((col) => (
                <th
                  key={col}
                  className="text-left px-3 py-2.5 font-semibold text-gray-600 bg-gray-50 first:rounded-tl-lg last:rounded-tr-lg whitespace-nowrap"
                >
                  {colLabel(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, ri) => (
              <tr key={ri} className="border-b border-gray-100 hover:bg-emerald-50/30 transition-colors">
                {columns.map((col) => (
                  <td key={col} className="px-3 py-2.5 text-gray-700 whitespace-nowrap">
                    {fmt(row[col], col)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-gray-400 mt-2 text-right">
          共 {data.length} 条记录
        </p>
      </div>
    );
  }

  return null;
}
