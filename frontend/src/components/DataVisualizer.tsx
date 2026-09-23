"use client";

import { useEffect, useRef, useState } from "react";

interface DataVisualizerProps {
  chartType?: string;
  echartsOption?: Record<string, unknown>;
  columns: string[];
  data: Record<string, unknown>[];
  viewMode: "chart" | "table";
}

// [FIX] CDN 加载 ECharts（绕开 static export 下 dynamic chunk 不生成的 bug）
// 原因：next.config.mjs 设了 output:"export"（Netlify 部署），
// dynamic(() => import("echarts-for-react"), {ssr:false}) 在静态导出时
// 不会把 echarts-for-react 打成分离 chunk，导致浏览器永远拿不到 ReactECharts。
// 改用 CDN 引入 echarts 本体，用 ref + echarts.init 直接渲染图表。
const ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js";

function loadEchartsFromCDN(): Promise<any> {
  return new Promise((resolve, reject) => {
    // 已被加载过（window.echarts）
    const w = window as any;
    if (w.echarts) {
      resolve(w.echarts);
      return;
    }
    // 已存在 script 节点（并发请求去重）
    const existing = document.querySelector(`script[src="${ECHARTS_CDN}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve((window as any).echarts));
      existing.addEventListener("error", reject);
      return;
    }
    const script = document.createElement("script");
    script.src = ECHARTS_CDN;
    script.async = true;
    script.onload = () => resolve((window as any).echarts);
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

function EChartsCanvas({ option }: { option: Record<string, unknown> }) {
  const ref = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<any>(null);
  const [loadStatus, setLoadStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let mounted = true;
    loadEchartsFromCDN()
      .then((echarts) => {
        if (!mounted) return;
        if (!ref.current) return;
        instanceRef.current = echarts.init(ref.current, undefined, { renderer: "canvas" });
        instanceRef.current.setOption(option, true);
        setLoadStatus("ready");
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error("[ECharts] CDN load failed:", err);
        setLoadStatus("error");
      });
    return () => {
      mounted = false;
      if (instanceRef.current) {
        instanceRef.current.dispose();
        instanceRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // option 变化时更新
  useEffect(() => {
    if (instanceRef.current) {
      instanceRef.current.setOption(option, true);
    }
  }, [option]);

  // 容器尺寸自适应
  useEffect(() => {
    if (!ref.current || !instanceRef.current) return;
    const ro = new ResizeObserver(() => instanceRef.current?.resize());
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [loadStatus]);

  if (loadStatus === "error") {
    return (
      <div className="text-sm text-red-500 p-4 border border-red-200 rounded">
        ⚠️ 图表加载失败：ECharts CDN 不可用
      </div>
    );
  }

  return (
    <div className="relative">
      <div ref={ref} style={{ height: "320px", width: "100%" }} />
      {loadStatus === "loading" && (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-400 bg-white/60">
          📊 图表加载中...
        </div>
      )}
    </div>
  );
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
  // [FIX] funnel 类型走 ECharts 渲染（之前会被 fallback 到 table）
  if (viewMode === "chart" && echartsOption && chartType !== "table" && chartType !== "single_kpi") {
    return <EChartsCanvas option={echartsOption} />;
  }

  // [FIX] single_kpi 在 chart 视图下也走 KPI 卡片渲染（不是 ECharts）
  if (chartType === "single_kpi" && data && data.length === 1) {
    const row = data[0];
    const isChartView = viewMode === "chart";
    return (
      <div className={`grid grid-cols-${columns.length > 1 ? "2" : "1"} gap-4 py-4 ${isChartView ? "bg-gradient-to-br from-emerald-50/60 via-white to-blue-50/60 -mx-2 px-4 rounded-lg" : ""}`}>
        {columns.map((col) => (
          <div key={col} className="bg-gradient-to-br from-emerald-50 to-blue-50 rounded-lg p-5 border border-emerald-100 shadow-sm">
            <p className="text-xs text-gray-500 mb-1.5 font-medium">{colLabel(col)}</p>
            <p className="text-3xl font-bold text-emerald-700 tracking-tight">{fmt(row[col], col)}</p>
          </div>
        ))}
      </div>
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
