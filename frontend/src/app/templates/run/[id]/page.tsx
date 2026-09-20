"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import dynamic from "next/dynamic";
import {
  Loader2, ChevronLeft, AlertTriangle, CheckCircle2, Info, Clock,
  TrendingUp, TrendingDown, Minus, Download, FileText, Database,
} from "lucide-react";
import {
  v2RunTemplate, getTemplate, STEP_TYPE_META, TemplateRunResponse, Template,
} from "@/lib/templates-api";

// ECharts 客户端动态导入（SSR 安全）
const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

const STATUS_STYLES: Record<string, { bg: string; text: string; icon: any; label: string }> = {
  ok:   { bg: "bg-emerald-50 border-emerald-200", text: "text-emerald-700", icon: CheckCircle2, label: "正常" },
  warn: { bg: "bg-amber-50 border-amber-200",     text: "text-amber-700",   icon: AlertTriangle, label: "预警" },
  bad:  { bg: "bg-red-50 border-red-200",         text: "text-red-700",     icon: AlertTriangle, label: "异常" },
  info: { bg: "bg-blue-50 border-blue-200",       text: "text-blue-700",    icon: Info, label: "信息" },
};

export default function TemplateRunPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const templateId = params?.id || "";

  const [tpl, setTpl] = useState<Template | null>(null);
  const [result, setResult] = useState<TemplateRunResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const r = await v2RunTemplate(templateId, {});
      setResult(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const t = await getTemplate(templateId);
        if (!t) {
          setError("模板不存在");
          return;
        }
        setTpl(t);
        await run();
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templateId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
        <span className="ml-2 text-sm text-gray-500">启动 SOP 引擎...</span>
      </div>
    );
  }

  if (error || !tpl) {
    return (
      <div className="min-h-screen p-8">
        <div className="max-w-2xl mx-auto">
          <button
            onClick={() => router.push("/templates")}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3"
          >
            <ChevronLeft className="w-4 h-4" />
            返回模板中心
          </button>
          <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded text-sm text-red-800">
            {error || "模板不存在"}
          </div>
        </div>
      </div>
    );
  }

  const summaryStats = result
    ? {
        total: result.report.length,
        ok: result.report.filter((s) => s.status === "ok").length,
        warn: result.report.filter((s) => s.status === "warn").length,
        bad: result.report.filter((s) => s.status === "bad").length,
        totalMs: result.total_execution_time_ms,
      }
    : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-purple-50">
      {/* 顶部 */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <button
              onClick={() => router.push("/templates")}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 mb-1"
            >
              <ChevronLeft className="w-3 h-3" />
              返回模板中心
            </button>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-600" />
              {tpl.name}
              <span className="text-xs font-normal text-gray-500 ml-2">
                SOP 归因报告
              </span>
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={run}
              disabled={running}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50"
            >
              {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <TrendingUp className="w-3 h-3" />}
              {running ? "执行中..." : "重新执行"}
            </button>
            <button
              onClick={() => router.push(`/templates/editor/${tpl.id}`)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
            >
              <Database className="w-3 h-3" />
              查看模板
            </button>
          </div>
        </div>
      </header>

      {/* 高管摘要卡 */}
      {result && summaryStats && (
        <section className="max-w-6xl mx-auto px-6 pt-6">
          <div className="bg-gradient-to-br from-purple-600 to-indigo-600 rounded-2xl shadow-lg p-6 text-white">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="text-xs opacity-80 mb-1">高管摘要</div>
                <div className="text-lg font-semibold leading-relaxed mb-3">
                  {result.executive_summary}
                </div>
                <div className="flex flex-wrap gap-3 text-xs">
                  <span className="px-2 py-1 bg-white/15 rounded">
                    📊 共 {summaryStats.total} 步
                  </span>
                  {summaryStats.bad > 0 && (
                    <span className="px-2 py-1 bg-red-500/80 rounded">
                      🚨 {summaryStats.bad} 项异常
                    </span>
                  )}
                  {summaryStats.warn > 0 && (
                    <span className="px-2 py-1 bg-amber-500/80 rounded">
                      ⚠️ {summaryStats.warn} 项预警
                    </span>
                  )}
                  <span className="px-2 py-1 bg-emerald-500/80 rounded">
                    ✔ {summaryStats.ok} 项正常
                  </span>
                  <span className="px-2 py-1 bg-white/15 rounded flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {summaryStats.totalMs.toFixed(0)}ms
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 步骤详情 */}
      {result && (
        <section className="max-w-6xl mx-auto px-6 py-6 space-y-4">
          {result.report.map((s, i) => {
            const style = STATUS_STYLES[s.status] || STATUS_STYLES.info;
            const Icon = style.icon;
            const meta = STEP_TYPE_META[s.step_type as keyof typeof STEP_TYPE_META];
            // 兜底 order：后端可能不返回，使用下标 + 1
            const stepOrder = (s as any).order ?? (i + 1);
            return (
              <div
                key={s.step_id}
                className={`bg-white rounded-xl border p-5 ${style.bg}`}
              >
                {/* Step Header */}
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl bg-white border border-gray-200 flex items-center justify-center flex-shrink-0">
                    <span className="text-xl">{meta?.icon}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-gray-400">Step {stepOrder}</span>
                      <Icon className={`w-4 h-4 ${style.text}`} />
                      <span className={`text-xs font-semibold ${style.text}`}>
                        [{style.label}]
                      </span>
                      <h3 className="text-base font-semibold text-gray-900">{s.title}</h3>
                      <span className="text-[10px] text-gray-400 px-1.5 py-0.5 bg-gray-100 rounded">
                        {s.step_type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed mt-2">{s.conclusion}</p>
                  </div>
                  <div className="text-right text-xs text-gray-400 flex-shrink-0">
                    <div>{s.execution_time_ms}ms</div>
                    <div>{s.row_count} 行</div>
                    <div>{s.engine}</div>
                  </div>
                </div>

                {/* 数据表 + 图表 */}
                {s.data && s.data.length > 0 && (
                  <div className="grid grid-cols-12 gap-4">
                    {/* 数据表 */}
                    <div className="col-span-7 bg-white rounded border border-gray-200 overflow-hidden">
                      <div className="bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-700 border-b">
                        数据明细（前 {Math.min(10, s.data.length)} 行）
                      </div>
                      <div className="overflow-x-auto max-h-64">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="bg-gray-50">
                              {(s.columns || Object.keys(s.data[0])).map((c) => (
                                <th key={c} className="px-3 py-2 text-left text-gray-500 font-medium">
                                  {c}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {s.data.slice(0, 10).map((row, ri) => (
                              <tr key={ri} className="border-t border-gray-100 hover:bg-gray-50">
                                {(s.columns || Object.keys(row)).map((c) => (
                                  <td key={c} className="px-3 py-1.5 text-gray-700">
                                    {typeof row[c] === "number"
                                      ? row[c].toLocaleString(undefined, { maximumFractionDigits: 2 })
                                      : String(row[c])}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* ECharts 图表 */}
                    <div className="col-span-5 bg-white rounded border border-gray-200 p-2">
                      <StepChart step={s} />
                    </div>
                  </div>
                )}

                {/* 错误提示 */}
                {s.error && (
                  <div className="mt-3 bg-red-50 border-l-4 border-red-400 p-2 rounded text-xs text-red-700">
                    <strong>执行错误：</strong>{s.error}
                  </div>
                )}

                {/* SQL 折叠（高级用户查看） */}
                {s.sql && (
                  <details className="mt-3">
                    <summary className="text-[10px] text-gray-400 cursor-pointer hover:text-gray-600">
                      查看 SQL
                    </summary>
                    <pre className="mt-2 bg-gray-900 text-green-300 text-[10px] p-3 rounded overflow-x-auto">
                      {s.sql}
                    </pre>
                  </details>
                )}
              </div>
            );
          })}
        </section>
      )}

      {!result && !error && (
        <section className="max-w-6xl mx-auto px-6 py-12 text-center">
          <Loader2 className="w-6 h-6 animate-spin text-purple-600 mx-auto" />
          <p className="text-sm text-gray-500 mt-2">正在执行 SOP...</p>
        </section>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// 单步骤 ECharts 图表（按 step_type 自动选型）
// ────────────────────────────────────────────────────────────
function StepChart({ step }: { step: any }) {
  const data = step.data || [];
  if (data.length === 0) {
    return <div className="text-center text-xs text-gray-400 py-10">无数据</div>;
  }

  const cols = step.columns || Object.keys(data[0]);
  const labelCol = cols[0];  // 第一列通常是分组维度
  const valueCol = cols[cols.length - 1];  // 最后一列是数值

  // 横轴标签 + 纵轴数据
  const labels = data.map((r: any) => String(r[labelCol] ?? ""));
  const values = data.map((r: any) => Number(r[valueCol] ?? 0));

  // overall_kpi: KPI 大数字
  if (step.step_type === "overall_kpi") {
    const row = data[0] || {};
    return (
      <div className="space-y-2">
        <KpiBlock label="实际" value={row.actual} color="blue" />
        <KpiBlock label="目标" value={row.plan} color="gray" />
        <KpiBlock
          label="达成率"
          value={row.fulfillment_rate ? (row.fulfillment_rate * 100).toFixed(2) + "%" : "-"}
          color={row.fulfillment_rate < 0.85 ? "red" : row.fulfillment_rate < 0.95 ? "amber" : "emerald"}
        />
      </div>
    );
  }

  // yoy_compare / period_compare: 双数值对比
  if (step.step_type === "yoy_compare" || step.step_type === "period_compare") {
    const row = data[0] || {};
    return (
      <ReactECharts
        option={{
          tooltip: { trigger: "item" },
          legend: { bottom: 0, textStyle: { fontSize: 10 } },
          series: [
            {
              type: "pie",
              radius: ["40%", "70%"],
              data: [
                { name: "本期", value: Number(row.current_actual || 0), itemStyle: { color: "#8b5cf6" } },
                { name: "上期", value: Number(row.prior_actual || 0), itemStyle: { color: "#d1d5db" } },
              ],
              label: { fontSize: 10 },
            },
          ],
        }}
        style={{ height: 200 }}
        opts={{ renderer: "svg" }}
      />
    );
  }

  // cross_attribution: 横向条形图
  if (step.step_type === "cross_attribution") {
    const sorted = [...data].sort((a, b) => Number(b.contribution_pct || 0) - Number(a.contribution_pct || 0));
    return (
      <ReactECharts
        option={{
          tooltip: { trigger: "axis" },
          grid: { left: 60, right: 20, top: 10, bottom: 20 },
          xAxis: { type: "value", axisLabel: { fontSize: 9 } },
          yAxis: { type: "category", data: sorted.map((r: any) => String(r[labelCol])), axisLabel: { fontSize: 9 } },
          series: [{
            type: "bar",
            data: sorted.map((r: any) => Number(r.contribution_pct || 0)),
            itemStyle: { color: "#8b5cf6" },
          }],
        }}
        style={{ height: 200 }}
        opts={{ renderer: "svg" }}
      />
    );
  }

  // anomaly_alert: z-score 散点
  if (step.step_type === "anomaly_alert") {
    return (
      <ReactECharts
        option={{
          tooltip: { trigger: "item" },
          grid: { left: 40, right: 20, top: 10, bottom: 30 },
          xAxis: { type: "category", data: labels, axisLabel: { fontSize: 9, rotate: 30 } },
          yAxis: { type: "value", axisLabel: { fontSize: 9 } },
          series: [{
            type: "bar",
            data: values.map((v: number, i: number) => ({
              value: v,
              itemStyle: {
                color: Math.abs(values[i]) > 1.5 ? "#ef4444" : Math.abs(values[i]) > 1 ? "#f59e0b" : "#10b981",
              },
            })),
          }],
        }}
        style={{ height: 200 }}
        opts={{ renderer: "svg" }}
      />
    );
  }

  // 默认：horizontal_compare / drill_down 用柱状图
  return (
    <ReactECharts
      option={{
        tooltip: { trigger: "axis" },
        grid: { left: 40, right: 20, top: 10, bottom: 30 },
        xAxis: {
          type: "category",
          data: labels,
          axisLabel: { fontSize: 9, rotate: labels.length > 4 ? 30 : 0 },
        },
        yAxis: { type: "value", axisLabel: { fontSize: 9 } },
        series: [{
          type: "bar",
          data: values,
          itemStyle: { color: "#6366f1", borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: "top", fontSize: 9, formatter: (p: any) => p.value.toLocaleString() },
        }],
      }}
      style={{ height: 200 }}
      opts={{ renderer: "svg" }}
    />
  );
}

// KPI 数字块
function KpiBlock({ label, value, color }: { label: string; value: any; color: string }) {
  const colorMap: Record<string, string> = {
    blue: "from-blue-500 to-blue-600",
    red: "from-red-500 to-red-600",
    amber: "from-amber-500 to-amber-600",
    emerald: "from-emerald-500 to-emerald-600",
    gray: "from-gray-400 to-gray-500",
  };
  return (
    <div className={`bg-gradient-to-r ${colorMap[color] || colorMap.blue} text-white rounded-lg p-3`}>
      <div className="text-[10px] opacity-80">{label}</div>
      <div className="text-xl font-bold mt-1">
        {typeof value === "number" ? value.toLocaleString() : value || "-"}
      </div>
    </div>
  );
}
