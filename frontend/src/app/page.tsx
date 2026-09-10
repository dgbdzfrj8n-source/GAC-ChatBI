"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Code2, ThumbsUp, ThumbsDown, BarChart3, Copy, Check } from "lucide-react";
import SuggestionPills from "@/components/SuggestionPills";
import ChatMessage from "@/components/ChatMessage";
import SqlDrawer from "@/components/SqlDrawer";
import BadCaseModal from "@/components/BadCaseModal";
import Sidebar from "@/components/Sidebar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface ChartResult {
  query: string;
  thought_steps: string[];
  sql: string;
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
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [showSql, setShowSql] = useState(false);
  const [showBadCase, setShowBadCase] = useState(false);
  const [copied, setCopied] = useState(false);
  const [currentResult, setCurrentResult] = useState<ChartResult | null>(null);
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setCurrentResult(null);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input.trim(), force_mock: false }),
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
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch {
      // 网络超时或服务未启动，自动降级 Mock 模式
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
    } finally {
      setLoading(false);
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
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* 左侧边栏 */}
      <Sidebar isOpen={showSidebar} onToggle={() => setShowSidebar(!showSidebar)} />

      {/* 主对话区 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部引导词 */}
        <div className="px-6 pt-4">
          <SuggestionPills onSuggestion={handleSuggestion} />
        </div>

        {/* 对话流 */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-16">
              <div className="text-5xl mb-4">🚗</div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">广汽云 ChatBI 智能问数</h2>
              <p className="text-gray-500 text-sm max-w-md mx-auto">
                基于集团真实经营数据，AI 驱动的自然语言问数与可视化分析助手。试试上方引导词或直接提问。
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              role={msg.role}
              content={msg.content}
              thoughtSteps={msg.result?.thought_steps}
              sql={msg.result?.sql}
              chartType={msg.result?.chart_type}
              echartsOption={msg.result?.echarts_option}
              columns={msg.result?.columns}
              data={msg.result?.data}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />
          ))}

          {loading && (
            <div className="flex items-start gap-3 animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                AI
              </div>
              <div className="bg-white rounded-2xl rounded-tl-sm border border-gray-200 px-4 py-3 shadow-sm">
                <div className="flex items-center gap-2 text-gray-500 text-sm">
                  <div className="w-3 h-3 rounded-full bg-emerald-500 animate-bounce" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.15s]" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.3s]" />
                  <span className="ml-1">正在分析中...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 底部操作栏（仅在有结果时显示） */}
        {currentResult && (
          <div className="px-6 pb-2 flex items-center gap-3 text-xs text-gray-500 border-t border-gray-200 pt-3 bg-white">
            <button
              onClick={() => setShowSql(!showSql)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200"
            >
              <Code2 className="w-3.5 h-3.5" />
              查看 SQL
            </button>

            <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200">
              <BarChart3 className="w-3.5 h-3.5" />
              钉入驾驶舱
            </button>

            <div className="flex-1" />

            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
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

        {/* SQL 抽屉 */}
        {showSql && currentResult?.sql && (
          <div className="px-6 pb-3">
            <SqlDrawer sql={currentResult.sql} onClose={() => setShowSql(false)} />
          </div>
        )}

        {/* 输入框 */}
        <div className="px-6 pb-6">
          <div className="relative">
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
            Shift+Enter 换行 · Enter 发送 · 支持自然语言问数与多轮追问
          </p>
        </div>
      </div>

      {/* Bad Case 弹窗 */}
      {showBadCase && (
        <BadCaseModal
          query={currentResult?.query || ""}
          sql={currentResult?.sql || ""}
          onClose={() => setShowBadCase(false)}
        />
      )}
    </div>
  );
}
