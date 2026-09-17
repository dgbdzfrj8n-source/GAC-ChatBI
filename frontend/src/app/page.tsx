"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authFetch, getUser, getToken, UserInfo } from "@/lib/auth";
import UserMenu from "@/components/UserMenu";
import {
  Send,
  Code2,
  ThumbsUp,
  ThumbsDown,
  BarChart3,
  Copy,
  Check,
  Activity,
  Microscope,
} from "lucide-react";
import SuggestionPills from "@/components/SuggestionPills";
import ChatMessage from "@/components/ChatMessage";
import SqlDrawer from "@/components/SqlDrawer";
import BadCaseModal from "@/components/BadCaseModal";
import SopResultModal from "@/components/SopResultModal";
import DimensionPicker from "@/components/DimensionPicker";
import { streamChat } from "@/lib/sse";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://gac-chatbi-api.onrender.com";
const USE_STREAMING = true; // Sprint 5.1: 启用 SSE 流式输出

interface ChartResult {
  query: string;
  thought_steps: string[];
  sql: string | null;
  success: boolean;
  data: Record<string, unknown>[];
  columns: string[];
  row_count: number;
  execution_time_ms: number;
  chart_type: string;
  echarts_option?: Record<string, unknown>;
  summary_insight: string;
  healed?: boolean;
  engine: string;
  error: string | null;
  is_meta_answer?: boolean;  // 闲聊/元问题兜底标识
  is_unsupported_entity?: boolean;  // 不可达维度拦截标识（门店/客户个体/未来预测）
}

// Mock 预置对话数据
const MOCK_WELCOME: ChartResult = {
  query: "2025年3月广汽埃安销量与预算达成率是多少？",
  thought_steps: [
    "命中集团经营指标：销售达成率",
    "经过 Schema 剪枝，锁定关联业务表：['fact_sales_daily', 'dim_budget_target']",
    "已命中车企高频离线经营知识，以 0-Latency 模式秒级响应",
    "正在通过 SQLite3 执行只读聚合查询...",
    "查询成功，耗时 6.35ms，获取 1 条经营聚合记录",
  ],
  sql: "WITH monthly_sales AS (...) SELECT ...",
  success: true,
  data: [
    {
      brand_name: "广汽埃安",
      year_month: "2025-03",
      actual_units: 4462,
      target_units: 4615,
      fulfillment_rate_pct: 96.68,
    },
  ],
  columns: ["brand_name", "year_month", "actual_units", "target_units", "fulfillment_rate_pct"],
  row_count: 1,
  execution_time_ms: 6.35,
  chart_type: "dual_axis",
  echarts_option: undefined,
  summary_insight:
    "2025年3月广汽埃安实际完成交付 4,462 辆，预算目标为 4,615 辆，综合达成率为 96.68%，整体表现稳健，距离月度目标仅存 153 辆缺口。",
  healed: false,
  engine: "SQLite3",
  error: null,
};

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: ChartResult;
  /** Sprint 5.1: 流式思考步骤（实时追加） */
  liveThoughts?: string[];
}

export default function ChatPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null);

  // [Sprint 10] 鉴权守卫：未登录跳 /login
  useEffect(() => {
    const u = getUser();
    const t = getToken();
    if (!u || !t) {
      router.push("/login");
      return;
    }
    setCurrentUser(u);
  }, [router]);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [showSql, setShowSql] = useState(false);
  const [showBadCase, setShowBadCase] = useState(false);
  const [showSop, setShowSop] = useState(false);
  const [sopData, setSopData] = useState<any>(null);
  const [sopLoading, setSopLoading] = useState(false);
  // ⭐ P0: 归因维度选择器状态
  const [showDimPicker, setShowDimPicker] = useState(false);
  const [pendingBrand, setPendingBrand] = useState<string>("");
  const [pendingYm, setPendingYm] = useState<string>("");
  const [copied, setCopied] = useState(false);
  const [currentResult, setCurrentResult] = useState<ChartResult | null>(null);
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");
  const [streamStatus, setStreamStatus] = useState<string>("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 演示模式结束 → 自动填入示例问句
  useEffect(() => {
    const pending = localStorage.getItem('gac-tour-pending-query');
    if (pending) {
      localStorage.removeItem('gac-tour-pending-query');
      setInput(pending);
      setTimeout(() => inputRef.current?.focus(), 200);
    }
  }, []);

  /**
   * P2-1 增强: 数据管理「明细」跳转 → 跳过 NL2SQL，直接调用 /api/data/details
   * URL: /?pending=DETAILS_TABLE:<table_name>:<source>
   *      或 localStorage gac-pending-query (兼容老格式)
   */
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const pendingParam = params.get('pending');
    const pendingStorage = localStorage.getItem('gac-pending-query');
    const pending = pendingParam || pendingStorage;
    if (pending) {
      localStorage.removeItem('gac-pending-query');

      // 清理 URL 上的 pending 参数
      if (pendingParam) {
        const url = new URL(window.location.href);
        url.searchParams.delete('pending');
        window.history.replaceState({}, '', url.pathname);
      }

      // === 新协议：DETAILS_TABLE:<table>:<source> → 直接拉明细，不走 NL2SQL ===
      if (pending.startsWith('DETAILS_TABLE:')) {
        const parts = pending.split(':');
        const tableName = parts[1];
        const source: 'user' | 'business' = parts[2] === 'business' ? 'business' : 'user';
        handleDirectDetails(tableName, source);
        return;
      }

      // === 兼容老协议：自由文本 query → 仍然填入输入框，用户点发送走 NL2SQL ===
      setInput(pending);
      setTimeout(() => inputRef.current?.focus(), 200);
    }
  }, []);

  /**
   * P2-1 修复: 直接查询明细（跳过 NL2SQL）
   * 数据管理「明细」按钮跳转时调用，确保返回的图表与"明细"语义匹配
   */
  const handleDirectDetails = async (tableName: string, source: 'user' | 'business' = 'user') => {
    setLoading(true);
    setCurrentResult(null);
    setStreamStatus("🔍 正在拉取明细...");

    const query = `查看 ${tableName} 表的前 20 行明细`;
    const userMsgId = Date.now().toString();
    const assistantId = (Date.now() + 1).toString();

    // 先放用户问句 + AI 占位
    setMessages((prev: Message[]) => [
      ...prev,
      {
        id: userMsgId,
        role: "user",
        content: query,
      },
      {
        id: assistantId,
        role: "assistant",
        content: "",
        liveThoughts: [],
        result: undefined,
      },
    ]);

    try {
      const r = await authFetch(
        `${API_URL}/api/data/details/${encodeURIComponent(tableName)}?limit=20&source=${source}`
      );
      const result = await r.json();
      if (!r.ok) throw new Error(result.detail || "明细查询失败");

      // 包装成 ChatResult 格式（chart_type 由后端智能判断：可能 line/bar/table）
      const chartType = (result.chart_type || "table") as "line" | "bar" | "table";
      const chatResult: ChartResult = {
        query,
        thought_steps: [
          `🎯 命中「明细查询」专用通道（跳过 NL2SQL）`,
          `📊 目标表：${result.table_name}（共 ${result.row_count.toLocaleString()} 行）`,
          `🗂️ 已按 ${result.order_by || '默认顺序'} 倒序展示前 ${result.data.length} 行`,
          `💡 明细可切图表视图：${chartType === 'table' ? '当前数据无适合图表，按表格展示' : `已自动生成 ${chartType === 'line' ? '趋势折线' : '柱状'}图`}`,
        ],
        sql: result.order_by
          ? `SELECT * FROM ${result.table_name} ORDER BY ${result.order_by} DESC LIMIT 20`
          : `SELECT * FROM ${result.table_name} LIMIT 20`,
        success: true,
        data: result.data,
        columns: result.columns.map((c: any) => c.name),
        row_count: result.data.length,
        execution_time_ms: 0,
        chart_type: chartType,                 // 智能判断
        echarts_option: result.echarts_option, // 后端生成的图表
        summary_insight: result.summary,
        engine: "direct_details",
        error: null,
      };

      // 替换 AI 占位
      setMessages((prev: Message[]) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: chartType === 'table' ? '✅ 明细已加载（表格视图）' : `✅ 明细已加载（自动${chartType === 'line' ? '折线' : '柱状'}图）`, result: chatResult }
            : m
        )
      );
      setCurrentResult(chatResult);
      setViewMode(chartType === 'table' ? 'table' : 'chart');  // 有图表就展示图表，否则直接表格
      setStreamStatus("");
    } catch (e: any) {
      const errResult: ChartResult = {
        query,
        thought_steps: [`❌ 明细查询失败：${e.message}`],
        sql: "",
        success: false,
        data: [],
        columns: [],
        row_count: 0,
        execution_time_ms: 0,
        chart_type: "table",
        summary_insight: `明细查询失败：${e.message}`,
        engine: "error",
        error: e.message,
      };
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: "❌", result: errResult } : m
        )
      );
      setStreamStatus("");
    } finally {
      setLoading(false);
    }
  };

  /**
   * Sprint 5.1: SSE 流式问数主入口
   */
  const handleSendStream = async (query: string) => {
    setLoading(true);
    setCurrentResult(null);
    setStreamStatus("🔍 正在启动 Agent...");

    // 先放一个空 AI 消息占位，后续流式追加
    const assistantId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        liveThoughts: [],
        result: {
          query,
          thought_steps: [],
          sql: "",
          success: false,
          data: [],
          columns: [],
          row_count: 0,
          execution_time_ms: 0,
          chart_type: "table",
          summary_insight: "",
          healed: false,
          engine: "DuckDB",
          error: null,
        },
      },
    ]);

    const accumulated: Partial<ChartResult> = {
      query,
      thought_steps: [],
      sql: "",
      success: false,
      data: [],
      columns: [],
      row_count: 0,
      execution_time_ms: 0,
      chart_type: "table",
      summary_insight: "",
      healed: false,
      engine: "DuckDB",
      error: null,
    };

    abortRef.current = new AbortController();

    try {
      await streamChat(
        query,
        {
          onThought: ({ step, text }) => {
            setStreamStatus(`💭 ${text}`);
            accumulated.thought_steps = [...(accumulated.thought_steps || []), text];
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      liveThoughts: [...(m.liveThoughts || []), text],
                      result: { ...(m.result as ChartResult), thought_steps: m.result?.thought_steps || [] },
                    }
                  : m
              )
            );
          },
          onSql: ({ sql }) => {
            accumulated.sql = sql;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, result: { ...(m.result as ChartResult), sql } } : m
              )
            );
          },
          onData: (data) => {
            accumulated.data = data.rows;
            accumulated.columns = data.columns;
            accumulated.row_count = data.row_count;
            accumulated.execution_time_ms = data.execution_time_ms;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      result: {
                        ...(m.result as ChartResult),
                        data: data.rows,
                        columns: data.columns,
                        row_count: data.row_count,
                        execution_time_ms: data.execution_time_ms,
                      },
                    }
                  : m
              )
            );
          },
          onChart: ({ chart_type, echarts_option }) => {
            accumulated.chart_type = chart_type;
            accumulated.echarts_option = echarts_option;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      result: {
                        ...(m.result as ChartResult),
                        chart_type,
                        echarts_option,
                      },
                    }
                  : m
              )
            );
          },
          onInsightStart: () => {
            setStreamStatus("📝 经营分析师正在撰写洞察...");
          },
          onInsight: (text) => {
            accumulated.summary_insight = (accumulated.summary_insight || "") + text;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + text }
                  : m
              )
            );
          },
          onMetaAnswer: (text) => {
            // 闲聊/元问题回复
            accumulated.is_meta_answer = true;
            accumulated.summary_insight = (accumulated.summary_insight || "") + text;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + text }
                  : m
              )
            );
          },
          onDone: (data) => {
            accumulated.success = data.success;
            accumulated.healed = data.healed;
            accumulated.engine = data.engine as any;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, result: { ...(m.result as ChartResult), ...accumulated } as ChartResult }
                  : m
              )
            );
            setCurrentResult(accumulated as ChartResult);
            setStreamStatus("");
          },
          onError: (error) => {
            setStreamStatus(`❌ 错误: ${error}`);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, result: { ...(m.result as ChartResult), error, success: false } }
                  : m
              )
            );
          },
        },
        abortRef.current.signal
      );
    } catch (err) {
      // 网络失败 → 降级 Mock
      console.warn("SSE 失败，降级 Mock:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: MOCK_WELCOME.summary_insight, result: MOCK_WELCOME }
            : m
        )
      );
      setCurrentResult(MOCK_WELCOME);
      setStreamStatus("");
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  /**
   * 非流式 /api/chat（兼容模式）
   */
  const handleSendBlocking = async (query: string) => {
    try {
      const res = await authFetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, force_mock: false }),
      });

      if (res.ok) {
        const data = await res.json();
        setCurrentResult(data);
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: data.summary_insight || "查询完成",
            result: data,
          },
        ]);
        // P2-5: 派发问数完成通知
        window.dispatchEvent(
          new CustomEvent('gac-notification', {
            detail: {
              type: 'new_question',
              severity: 'info',
              title: `💬 已完成问数：${query.slice(0, 24)}${query.length > 24 ? '…' : ''}`,
              body: `耗时 ${data.execution_time_ms?.toFixed?.(0) ?? '?'}ms，返回 ${data.row_count ?? 0} 行`,
              link: '/',
            },
          })
        );
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: MOCK_WELCOME.summary_insight,
          result: MOCK_WELCOME,
        },
      ]);
      setCurrentResult(MOCK_WELCOME);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
    };
    setMessages((prev) => [...prev, userMsg]);
    const query = input.trim();
    setInput("");
    setLoading(true);
    setCurrentResult(null);

    try {
      if (USE_STREAMING) {
        await handleSendStream(query);
      } else {
        await handleSendBlocking(query);
      }
    } finally {
      setLoading(false);
    }
  };

  /**
   * Sprint 5.3: 触发 SOP 归因分析
   */
  const handleSopAnalyze = async () => {
    if (!currentResult) return;
    // 推断品牌和月份
    const brand =
      (currentResult.data[0]?.brand_name as string) ||
      (currentResult.data[0]?.brand as string) ||
      "广汽埃安";
    const ym = (currentResult.data[0]?.year_month as string) || "2025-03";

    // ⭐ P0: 先弹出归因维度选择器（用户自定义归因维度）
    setPendingBrand(brand);
    setPendingYm(ym);
    setShowDimPicker(true);
  };

  // ⭐ P0 + P1 新增：用户选完维度 + 指标后真正执行 SOP 分析
  const executeSopWithDimensions = async (selectedDimensions: string[], metricKey: string = "delivered_units") => {
    setShowDimPicker(false);
    const brand = pendingBrand;
    const ym = pendingYm;

    setSopLoading(true);
    setShowSop(true);
    try {
      const res = await authFetch(`${API_URL}/api/sop/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_name: brand,
          year_month: ym,
          threshold_pct: 95,
          selected_dimensions: selectedDimensions,  // ⭐ P0 新增参数
          metric_key: metricKey,                     // ⭐ P1 新增参数
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSopData(data);
        // P2-5: 派发 SOP 完成通知
        window.dispatchEvent(
          new CustomEvent('gac-notification', {
            detail: {
              type: 'sop_complete',
              severity: 'success',
              title: `🔍 深度归因完成：${brand} ${ym}`,
              body: `基于 ${selectedDimensions.length} 个维度，已生成归因报告`,
              link: '/',
              audience: ['executive', 'analyst', 'product'],
            },
          })
        );
      } else {
        setSopData({ error: `HTTP ${res.status}` });
      }
    } catch (e: any) {
      setSopData({ error: e.message || "SOP 调用失败" });
    } finally {
      setSopLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = () => {
    if (currentResult?.sql) {
      navigator.clipboard.writeText(currentResult.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSuggestion = (text: string) => {
    setInput(text);
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-full px-6 py-4">
      {/* 快捷提问 + 大屏入口 + 用户胶囊 */}
      <div className="flex items-start justify-between gap-4 mb-4 flex-shrink-0">
        <div className="flex-1">
          <SuggestionPills onSuggestion={handleSuggestion} />
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {currentUser && <UserMenu />}
          <a
            href="/dashboard"
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-all shadow-sm"
            title="进入管理驾驶舱大屏"
          >
            <Activity className="w-3.5 h-3.5" />
            驾驶舱大屏
          </a>
        </div>
      </div>

        {/* 对话流（可滚动区域） */}
        <div className="flex-1 overflow-y-auto space-y-4 scrollbar-thin">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="text-5xl mb-4">🚗</div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">广汽云 ChatBI 智能问数</h2>
              <p className="text-gray-500 text-sm max-w-md mx-auto">
                基于集团真实经营数据，AI 驱动的自然语言问数与可视化分析助手。
                <br />
                <span className="text-emerald-600 font-medium">
                  Sprint 9 已上线：15 条精准问数 · 指标维度合并 · 数据管理默认表 · 历史会话 4 功能
                </span>
              </p>
            </div>
          )}

          {messages.map((msg, idx) => {
            // 找该 assistant 消息的前一条 user 消息作为 query
            let prevUserQuery = '';
            for (let i = idx - 1; i >= 0; i--) {
              if (messages[i].role === 'user') {
                prevUserQuery = messages[i].content;
                break;
              }
            }
            return (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                content={msg.content}
                thoughtSteps={msg.liveThoughts || msg.result?.thought_steps}
                sql={msg.result?.sql}
                chartType={msg.result?.chart_type}
                echartsOption={msg.result?.echarts_option}
                columns={msg.result?.columns}
                data={msg.result?.data}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
                isMetaAnswer={msg.result?.is_meta_answer}
                isUnsupportedEntity={msg.result?.is_unsupported_entity}
                userQuery={prevUserQuery}
              />
            );
          })}

          {loading && (
            <div className="flex items-start gap-3 animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                AI
              </div>
              <div className="bg-white rounded-2xl rounded-tl-sm border border-gray-200 px-4 py-3 shadow-sm flex-1">
                <div className="flex items-center gap-2 text-gray-600 text-sm">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" />
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.15s]" />
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.3s]" />
                  </div>
                  <span className="ml-1">{streamStatus || "正在分析中..."}</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />

        {/* 底部操作栏 */}
        {currentResult && (
          <div className="flex-shrink-0 px-2 py-2 flex items-center gap-2 text-xs text-gray-500 border-t border-gray-200 bg-white">
            <button
              onClick={() => setShowSql(!showSql)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200"
            >
              <Code2 className="w-3.5 h-3.5" />
              查看 SQL
            </button>

            <button
              onClick={handleSopAnalyze}
              data-tour="sop-button"
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-purple-50 hover:text-purple-600 hover:border-purple-200 transition-colors border border-gray-200"
              title="Sprint 5.3: 触发四步归因 SOP"
            >
              <Microscope className="w-3.5 h-3.5" />
              深度归因
            </button>

            <a
              href="/dashboard"
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200"
            >
              <BarChart3 className="w-3.5 h-3.5" />
              钉入驾驶舱
            </a>

            <div className="flex-1" />

            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-500" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              {copied ? "已复制" : "复制 SQL"}
            </button>

            <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors text-emerald-600">
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={() => setShowBadCase(true)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-red-50 transition-colors text-red-500"
            >
              <ThumbsDown className="w-3.5 h-3.5" />
              反馈
            </button>
          </div>
        )}
      </div>

      {/* SQL 抽屉 → 固定浮层 */}
      {showSql && currentResult?.sql && (
        <SqlDrawer sql={currentResult.sql} onClose={() => setShowSql(false)} />
      )}

      {/* 输入框 → 固定底部 */}
      <div className="flex-shrink-0 px-2 pt-3 pb-2 bg-white border-t border-gray-100">
        <div className="relative" data-tour="chat-input">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的经营分析问题，例如：2025年3月埃安销量与预算达成率是多少？"
            className="w-full resize-none rounded-2xl border border-gray-200 bg-white px-4 py-3 pr-12 text-sm shadow-sm
                       focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent
                       placeholder:text-gray-400"
            rows={1}
            style={{ maxHeight: "120px" }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="absolute right-2 bottom-2 w-9 h-9 rounded-xl bg-emerald-500 hover:bg-emerald-600
                       disabled:opacity-40 disabled:cursor-not-allowed
                       flex items-center justify-center text-white transition-all active:scale-95"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 mt-2">
          Shift+Enter 换行 · Enter 发送 · SSE 流式输出 · 深度归因 SOP · 驾驶舱大屏
        </p>
      </div>

      {/* Bad Case 弹窗 */}
      {showBadCase && (
        <BadCaseModal
          query={currentResult?.query || ""}
          sql={currentResult?.sql || ""}
          onClose={() => setShowBadCase(false)}
        />
      )}

      {/* SOP 归因弹窗 Sprint 5.3 */}
      {showSop && (
        <SopResultModal data={sopData} loading={sopLoading} onClose={() => setShowSop(false)} />
      )}

      {/* ⭐ P0 新增：归因维度选择器 */}
      {showDimPicker && (
        <DimensionPicker
          loading={sopLoading}
          onConfirm={executeSopWithDimensions}
          onCancel={() => setShowDimPicker(false)}
          currentRole={currentUser?.role || "executive"}
          currentUser={currentUser?.username || "admin"}
        />
      )}
    </div>
  );
}
