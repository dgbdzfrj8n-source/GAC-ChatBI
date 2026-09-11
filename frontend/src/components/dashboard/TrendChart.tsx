"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface TrendChartProps {
  data: Array<{ month: string; brand_name: string; units: number }>;
}

export default function TrendChart({ data }: TrendChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || !data.length) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    // 数据按 brand 分组
    const brandSet = new Set(data.map((d) => d.brand_name));
    const brands = Array.from(brandSet);

    const months = Array.from(new Set(data.map((d) => d.month))).sort();

    const series = brands.map((brand) => ({
      name: brand,
      type: "line",
      smooth: true,
      symbol: "circle",
      symbolSize: 8,
      lineStyle: { width: 3 },
      data: months.map((m) => {
        const found = data.find((d) => d.month === m && d.brand_name === brand);
        return found ? found.units : 0;
      }),
    }));

    const option = {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.95)",
        borderColor: "#475569",
        textStyle: { color: "#fff" },
      },
      legend: {
        data: brands,
        textStyle: { color: "#cbd5e1" },
        top: 0,
        right: 0,
      },
      grid: { left: 50, right: 30, top: 40, bottom: 40 },
      xAxis: {
        type: "category",
        data: months,
        axisLine: { lineStyle: { color: "#475569" } },
        axisLabel: { color: "#94a3b8", fontSize: 11 },
      },
      yAxis: {
        type: "value",
        axisLine: { lineStyle: { color: "#475569" } },
        axisLabel: { color: "#94a3b8", fontSize: 11 },
        splitLine: { lineStyle: { color: "#334155", type: "dashed" } },
      },
      color: ["#fbbf24", "#34d399", "#a78bfa"],
      series,
    };

    chartInstance.current.setOption(option, true);

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [data]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return <div ref={chartRef} style={{ width: "100%", height: "320px" }} />;
}
