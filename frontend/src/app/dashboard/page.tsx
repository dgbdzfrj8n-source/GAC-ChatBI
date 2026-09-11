"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Activity, TrendingUp, AlertTriangle, Car, DollarSign, Users, ArrowUpRight, ArrowDownRight, RefreshCw } from "lucide-react";

// ECharts 客户端动态加载（避免 SSR 水合冲突）
const TrendChart = dynamic(() => import("@/components/dashboard/TrendChart"), { ssr: false });
const BrandRanking = dynamic(() => import("@/components/dashboard/BrandRanking"), { ssr: false });

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface DashboardSnapshot {
  meta: { latest_month: string; prev_month: string; generated_at: string };
  kpis: {
    fulfillment_rate_pct: number;
    total_units: number;
    total_revenue_wan: number;
    avg_cpl: number;
  };
  trend: { data: any[]; columns: string[] };
  ranking: { data: any[]; columns: string[] };
  alerts: any[];
}

const MOCK_DASHBOARD: DashboardSnapshot = {
  meta: { latest_month: "2025-03", prev_month: "2025-02", generated_at: "演示数据" },
  kpis: { fulfillment_rate_pct: 99.25, total_units: 8498, total_revenue_wan: 139881.4, avg_cpl: 129.78 },
  trend: {
    data: [
      { month: "2024-04", brand_name: "广汽埃安", units: 3850 },
      { month: "2024-05", brand_name: "广汽埃安", units: 4120 },
      { month: "2024-06", brand_name: "广汽埃安", units: 4380 },
      { month: "2024-07", brand_name: "广汽埃安", units: 4520 },
      { month: "2024-08", brand_name: "广汽埃安", units: 4210 },
      { month: "2024-09", brand_name: "广汽埃安", units: 4680 },
      { month: "2024-10", brand_name: "广汽埃安", units: 4890 },
      { month: "2024-11", brand_name: "广汽埃安", units: 4520 },
      { month: "2024-12", brand_name: "广汽埃安", units: 4310 },
      { month: "2025-01", brand_name: "广汽埃安", units: 4180 },
      { month: "2025-02", brand_name: "广汽埃安", units: 4380 },
      { month: "2025-03", brand_name: "广汽埃安", units: 4462 },
      { month: "2024-04", brand_name: "广汽传祺", units: 2920 },
      { month: "2024-05", brand_name: "广汽传祺", units: 3050 },
      { month: "2024-06", brand_name: "广汽传祺", units: 3180 },
      { month: "2024-07", brand_name: "广汽传祺", units: 3120 },
      { month: "2024-08", brand_name: "广汽传祺", units: 2960 },
      { month: "2024-09", brand_name: "广汽传祺", units: 3280 },
      { month: "2024-10", brand_name: "广汽传祺", units: 3450 },
      { month: "2024-11", brand_name: "广汽传祺", units: 3320 },
      { month: "2024-12", brand_name: "广汽传祺", units: 3180 },
      { month: "2025-01", brand_name: "广汽传祺", units: 3050 },
      { month: "2025-02", brand_name: "广汽传祺", units: 3120 },
      { month: "2025-03", brand_name: "广汽传祺", units: 3223 },
      { month: "2024-04", brand_name: "昊铂", units: 680 },
      { month: "2024-05", brand_name: "昊铂", units: 720 },
      { month: "2024-06", brand_name: "昊铂", units: 760 },
      { month: "2024-07", brand_name: "昊铂", units: 690 },
      { month: "2024-08", brand_name: "昊铂", units: 720 },
      { month: "2024-09", brand_name: "昊铂", units: 780 },
      { month: "2024-10", brand_name: "昊铂", units: 800 },
      { month: "2024-11", brand_name: "昊铂", units: 750 },
      { month: "2024-12", brand_name: "昊铂", units: 720 },
      { month: "2025-01", brand_name: "昊铂", units: 711 },
      { month: "2025-02", brand_name: "昊铂", units: 374 },
      { month: "2025-03", brand_name: "昊铂", units: 813 },
    ],
    columns: ["month", "brand_name", "units"],
  },
  ranking: {
    data: [
      { brand_name: "广汽传祺", actual: 3223, target: 3142, fulfillment_rate: 102.58 },
      { brand_name: "昊铂", actual: 813, target: 805, fulfillment_rate: 100.99 },
      { brand_name: "广汽埃安", actual: 4462, target: 4615, fulfillment_rate: 96.68 },
    ],
    columns: ["brand_name", "actual", "target", "fulfillment_rate"],
  },
  alerts: [],
};

export default function DashboardPage() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [latestMonth, setLatestMonth] = useState("2025-03");
  const [usingMock, setUsingMock] = useState(false);

  const fetchSnapshot = async (ym: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/dashboard/snapshot?latest_month=${ym}`, {
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        setSnapshot(data);
        setUsingMock(false);
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch {
      // 降级 Mock
      setSnapshot(MOCK_DASHBOARD);
      setUsingMock(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSnapshot(latestMonth);
  }, [latestMonth]);

  const kpis = snapshot?.kpis;
  const ranking = snapshot?.ranking?.data || [];
  const alerts = snapshot?.alerts || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-slate-900">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wide">广汽集团经营驾驶舱</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              数据月份：{latestMonth} · {usingMock ? "📦 离线演示模式" : "✅ 实时数据"} ·
              上次刷新：{snapshot?.meta.generated_at?.slice(11, 19) || "—"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={latestMonth}
            onChange={(e) => setLatestMonth(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400"
          >
            <option value="2024-12">2024-12</option>
            <option value="2025-01">2025-01</option>
            <option value="2025-02">2025-02</option>
            <option value="2025-03">2025-03</option>
            <option value="2025-04">2025-04</option>
          </select>
          <button
            onClick={() => fetchSnapshot(latestMonth)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-900 text-sm font-medium transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            刷新
          </button>
          <a
            href="/"
            className="px-3 py-2 rounded-lg border border-slate-700 hover:border-slate-500 text-sm text-slate-300 transition-colors"
          >
            ← 返回对话
          </a>
        </div>
      </div>

      {loading && !snapshot ? (
        <div className="flex items-center justify-center h-96 text-slate-400">
          <RefreshCw className="w-8 h-8 animate-spin mr-2" />
          加载驾驶舱数据...
        </div>
      ) : (
        <>
          {/* 4 个 KPI 卡片 */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <KpiCard
              icon={<TrendingUp className="w-5 h-5" />}
              label="综合达成率"
              value={`${kpis?.fulfillment_rate_pct?.toFixed(2) || "0"}%`}
              tone="amber"
              trend={kpis?.fulfillment_rate_pct && kpis.fulfillment_rate_pct >= 95 ? "up" : "down"}
            />
            <KpiCard
              icon={<Car className="w-5 h-5" />}
              label="总交付量"
              value={`${(kpis?.total_units || 0).toLocaleString()} 辆`}
              tone="emerald"
            />
            <KpiCard
              icon={<DollarSign className="w-5 h-5" />}
              label="总营收"
              value={`${(kpis?.total_revenue_wan || 0).toLocaleString()} 万`}
              tone="blue"
            />
            <KpiCard
              icon={<Users className="w-5 h-5" />}
              label="平均 CPL"
              value={`¥${kpis?.avg_cpl?.toFixed(0) || "0"}`}
              tone="purple"
              trend="down"
              hint="越低越好"
            />
          </div>

          {/* 中间图表区 */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="col-span-2 bg-slate-800/50 backdrop-blur rounded-2xl p-5 border border-slate-700">
              <h3 className="text-sm font-semibold text-slate-200 mb-3">📈 近 12 月品牌交付趋势</h3>
              <TrendChart data={snapshot?.trend.data || []} />
            </div>
            <div className="bg-slate-800/50 backdrop-blur rounded-2xl p-5 border border-slate-700">
              <h3 className="text-sm font-semibold text-slate-200 mb-3">🏆 品牌达成率排名</h3>
              <BrandRanking data={ranking} />
            </div>
          </div>

          {/* 异常预警区 */}
          <div className="bg-slate-800/50 backdrop-blur rounded-2xl p-5 border border-slate-700">
            <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              经营预警与归因建议
            </h3>
            {alerts.length === 0 ? (
              <div className="text-center py-12 text-slate-500">
                <div className="text-3xl mb-2">✨</div>
                <div className="text-sm">当期所有品牌达成率 ≥ 95%，经营状态良好</div>
                <div className="text-xs text-slate-600 mt-1">持续监控中</div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {alerts.map((alert: any, idx: number) => (
                  <div
                    key={idx}
                    className="border border-red-800/50 bg-red-900/20 rounded-xl p-4"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-semibold text-red-300">{alert.brand}</div>
                      <div className="text-xs px-2 py-1 bg-red-500/20 text-red-300 rounded-full">
                        达成率 {alert.fulfillment_rate?.toFixed(2)}%
                      </div>
                    </div>
                    <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                      {alert.executive_summary}
                    </div>
                    {alert.top_recommendation && (
                      <div className="mt-3 p-3 bg-amber-900/20 border border-amber-700/30 rounded-lg">
                        <div className="text-xs font-semibold text-amber-300 mb-1">🎯 首要建议</div>
                        <div className="text-sm text-slate-200">{alert.top_recommendation.action}</div>
                        {alert.top_recommendation.budget_impact && (
                          <div className="text-xs text-slate-400 mt-1">
                            💰 {alert.top_recommendation.budget_impact}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 底部脚注 */}
          <div className="text-center text-xs text-slate-500 mt-6">
            <a href="/" className="hover:text-amber-400">← 返回 ChatBI 主对话</a>
            <span className="mx-3">·</span>
            <span>Sprint 5.2 实现 · 数据由 /api/dashboard/snapshot 实时聚合</span>
            <span className="mx-3">·</span>
            <span>© 广汽云 ChatBI</span>
          </div>
        </>
      )}
    </div>
  );
}

interface KpiCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: "amber" | "emerald" | "blue" | "purple";
  trend?: "up" | "down";
  hint?: string;
}

function KpiCard({ icon, label, value, tone, trend, hint }: KpiCardProps) {
  const toneClasses: Record<string, string> = {
    amber: "from-amber-400/20 to-amber-600/10 border-amber-500/30 text-amber-300",
    emerald: "from-emerald-400/20 to-emerald-600/10 border-emerald-500/30 text-emerald-300",
    blue: "from-blue-400/20 to-blue-600/10 border-blue-500/30 text-blue-300",
    purple: "from-purple-400/20 to-purple-600/10 border-purple-500/30 text-purple-300",
  };

  return (
    <div
      className={`bg-gradient-to-br ${toneClasses[tone]} backdrop-blur rounded-2xl p-5 border transition-transform hover:scale-[1.02]`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-medium text-slate-400">{label}</div>
        <div className={toneClasses[tone].split(" ").pop()}>{icon}</div>
      </div>
      <div className="text-3xl font-bold text-white tracking-tight">{value}</div>
      {trend && (
        <div className="flex items-center gap-1 mt-2 text-xs">
          {trend === "up" ? (
            <ArrowUpRight className="w-3 h-3 text-emerald-400" />
          ) : (
            <ArrowDownRight className="w-3 h-3 text-red-400" />
          )}
          <span className={trend === "up" ? "text-emerald-400" : "text-red-400"}>
            {hint || (trend === "up" ? "高于阈值" : "需要关注")}
          </span>
        </div>
      )}
    </div>
  );
}
