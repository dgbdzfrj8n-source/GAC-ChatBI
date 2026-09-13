"use client";

import { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, BarChart3, Table2 } from "lucide-react";
import DataVisualizer from "./DataVisualizer";
import FeedbackButtons from "./FeedbackButtons";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  thoughtSteps?: string[];
  sql?: string | null;
  chartType?: string;
  echartsOption?: Record<string, unknown>;
  columns?: string[];
  data?: Record<string, unknown>[];
  viewMode?: "chart" | "table";
  onViewModeChange?: (mode: "chart" | "table") => void;
  isMetaAnswer?: boolean;  // 闲聊/元问题兜底标识
  userQuery?: string;  // P2-7: 用户原始问题，反馈用
}

export default function ChatMessage({
  role,
  content,
  thoughtSteps,
  sql,
  chartType,
  echartsOption,
  columns,
  data,
  viewMode = "chart",
  onViewModeChange,
  isMetaAnswer = false,
  userQuery,
}: ChatMessageProps) {
  const [thoughtExpanded, setThoughtExpanded] = useState(false);
  // [P2-1 修复] 用 useEffect 同步父组件 viewMode prop，避免父组件切换时不联动
  const [localViewMode, setLocalViewMode] = useState<"chart" | "table">(viewMode);
  useEffect(() => {
    setLocalViewMode(viewMode);
  }, [viewMode]);

  if (role === "user") {
    return (
      <div className="flex justify-end animate-slide-up">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-emerald-500 text-white px-4 py-3 shadow-sm">
          <p className="text-sm leading-relaxed">{content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 animate-slide-up">
      {/* AI 头像 */}
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
        AI
      </div>

      <div className="flex-1 min-w-0">
        {/* 思考链折叠卡片 */}
        {thoughtSteps && thoughtSteps.length > 0 && (
          <details
            className="border-l-4 border-blue-400 bg-blue-50 rounded-r-xl p-3 mb-3 text-xs cursor-pointer group"
            open={thoughtExpanded}
            onToggle={(e) => setThoughtExpanded((e.target as HTMLDetailsElement).open)}
          >
            <summary className="flex items-center gap-2 font-semibold text-blue-700 list-none">
              {thoughtExpanded ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
              💡 经营分析师思考链（{thoughtSteps.length} 步）
            </summary>
            <div className="mt-2 space-y-1 text-gray-600 pl-5">
              {thoughtSteps.map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-blue-400 font-bold flex-shrink-0">{i + 1}.</span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </details>
        )}

        {/* 元问题/闲聊回复 */}
        {isMetaAnswer && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm mb-3">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                AI
              </div>
              <div className="flex-1">
                <p className="text-sm leading-relaxed text-gray-800 whitespace-pre-wrap">{content}</p>
              </div>
            </div>
          </div>
        )}

        {/* 经营洞察气泡（非元问题时显示） */}
        {!isMetaAnswer && (
          <div className="bg-white rounded-2xl rounded-tl-sm border border-gray-200 px-4 py-3 shadow-sm mb-3">
            <p className="text-sm leading-relaxed text-gray-800">{content}</p>
          </div>
        )}

        {/* 数据可视化（非元问题时显示） */}
        {!isMetaAnswer && data && data.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {/* Tab 切换 */}
            {onViewModeChange && (
              <div className="flex items-center border-b border-gray-200 px-4 pt-3">
                <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
                  <button
                    onClick={() => {
                      setLocalViewMode("chart");
                      onViewModeChange("chart");
                    }}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      localViewMode === "chart"
                        ? "bg-white shadow-sm text-emerald-700"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    <BarChart3 className="w-3.5 h-3.5" />
                    可视化图表
                  </button>
                  <button
                    onClick={() => {
                      setLocalViewMode("table");
                      onViewModeChange("table");
                    }}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      localViewMode === "table"
                        ? "bg-white shadow-sm text-emerald-700"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    <Table2 className="w-3.5 h-3.5" />
                    数据明细表
                  </button>
                </div>
                <div className="flex-1" />
                {chartType && (
                  <span className="text-xs text-gray-400">
                    图表类型：<span className="font-medium text-gray-600 capitalize">{chartType}</span>
                  </span>
                )}
              </div>
            )}

            {/* 图表 / 表格视图 */}
            <div className="p-4">
              <DataVisualizer
                chartType={chartType || "table"}
                echartsOption={echartsOption}
                columns={columns || []}
                data={data || []}
                viewMode={localViewMode}
              />
            </div>
          </div>
        )}

        {/* P2-7: Bad Case 反馈按钮（仅非闲聊且有数据时显示） */}
        {!isMetaAnswer && data && data.length > 0 && (
          <FeedbackButtons
            query={userQuery || ""}
            sql={sql || undefined}
            summary={content}
            messageId={`msg-${content.slice(0, 16)}`}
          />
        )}
      </div>
    </div>
  );
}
