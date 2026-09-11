"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface BrandRankingProps {
  data: Array<{ brand_name: string; actual: number; target: number; fulfillment_rate: number }>;
}

export default function BrandRanking({ data }: BrandRankingProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || !data.length) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const sorted = [...data].sort((a, b) => b.fulfillment_rate - a.fulfillment_rate);
    const brands = sorted.map((d) => d.brand_name);
    const rates = sorted.map((d) => d.fulfillment_rate);

    const colors = rates.map((r) => (r >= 100 ? "#34d399" : r >= 95 ? "#fbbf24" : "#f87171"));

    const option = {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.95)",
        borderColor: "#475569",
        textStyle: { color: "#fff" },
        formatter: (params: any) => {
          const idx = params[0].dataIndex;
          const d = sorted[idx];
          return `<b>${d.brand_name}</b><br/>
                  达成率: <b>${d.fulfillment_rate}%</b><br/>
                  实际: ${d.actual.toLocaleString()} 辆<br/>
                  目标: ${d.target.toLocaleString()} 辆`;
        },
      },
      grid: { left: 90, right: 50, top: 20, bottom: 20 },
      xAxis: {
        type: "value",
        max: 110,
        axisLine: { lineStyle: { color: "#475569" } },
        axisLabel: { color: "#94a3b8", fontSize: 10, formatter: "{value}%" },
        splitLine: { lineStyle: { color: "#334155", type: "dashed" } },
      },
      yAxis: {
        type: "category",
        data: brands,
        axisLine: { lineStyle: { color: "#475569" } },
        axisLabel: { color: "#e2e8f0", fontSize: 12, fontWeight: 600 },
      },
      series: [
        {
          type: "bar",
          data: rates.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
          barWidth: 22,
          label: {
            show: true,
            position: "right",
            formatter: "{c}%",
            color: "#fff",
            fontSize: 12,
            fontWeight: 600,
          },
        },
      ],
    };

    chartInstance.current.setOption(option, true);

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [data]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return <div ref={chartRef} style={{ width: "100%", height: "320px" }} />;
}
