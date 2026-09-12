'use client';

import { useState, useEffect } from "react";
import { X, Copy, Check, Info } from "lucide-react";

interface SqlDrawerProps {
  sql: string;
  onClose: () => void;
}

// DuckDB/SQLite 语法高亮
function highlightSql(sql: string): string {
  const keywords = [
    "SELECT", "FROM", "WHERE", "JOIN", "ON", "GROUP", "BY", "ORDER", "ASC", "DESC",
    "HAVING", "LIMIT", "WITH", "AS", "AND", "OR", "NOT", "NULLIF", "ROUND", "SUM",
    "STRFTIME", "CASE", "WHEN", "THEN", "ELSE", "END", "IN", "LIKE", "BETWEEN",
    "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS", "UNION", "ALL", "COUNT",
    "AVG", "MAX", "MIN", "DISTINCT", "COALESCE", "CAST",
  ];
  let result = sql
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // 字符串字面量（粉色）
    .replace(/'([^']*)'/g, "<span class='sql-string'>'$1'</span>")
    // 数字字面量（橙色）
    .replace(/\b(\d+(?:\.\d+)?)\b/g, "<span class='sql-number'>$1</span>")
    // 关键字（蓝色加粗）
    .replace(
      new RegExp(`\\b(${keywords.join("|")})\\b`, "gi"),
      "<span class='sql-keyword'>$1</span>"
    );
  // 注释（灰色斜体）
  result = result.replace(/(--[^\n]*)/g, "<span class='sql-comment'>$1</span>");
  return result;
}

// 字段中文解释
const FIELD_EXPLANATIONS: Record<string, string> = {
  brand_name: "品牌名称",
  year_month: "统计月份",
  actual_units: "实际交付量（辆）",
  target_units: "预算目标（辆）",
  fulfillment_rate_pct: "达成率（%）",
  total_delivered_units: "累计交付量（辆）",
  gross_revenue_billion_yuan: "总营收（亿元）",
  avg_price_yuan: "单车成交均价（元）",
  channel_name: "营销渠道",
  total_expense_wan: "投放支出（万元）",
  total_leads: "线索量（条）",
  cpl_yuan: "获客成本（元/条）",
  region_name: "销售大区",
  model_name: "车型名称",
  delivered_units: "交付数量（辆）",
  gross_revenue: "营收金额（元）",
  expense_amount: "费用金额（元）",
  leads_generated: "产生线索（条）",
  visits: "进店客流（人）",
  test_drive_count: "试驾次数（次）",
  orders: "成交订单（单）",
  conversion_rate: "转化率（%）",
  avg_marketing_cost_yuan: "单车营销费用（元）",
  month: "月份",
  units: "数量（辆）",
  revenue_wan: "营收（万元）",
};

function getFieldExplanation(col: string): string {
  return FIELD_EXPLANATIONS[col] || col;
}

export default function SqlDrawer({ sql, onClose }: SqlDrawerProps) {
  const [copied, setCopied] = useState(false);

  // ESC 键关闭
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // 提取 SELECT 字段（用于字段说明）
  const selectFieldsMatch = sql.match(/SELECT\s+([\s\S]*?)\s+FROM/i);
  const selectFields = selectFieldsMatch ? selectFieldsMatch[1] : '';
  const fieldNames = selectFields
    .split(',')
    .map((f: string) => f.trim().split(' AS ').pop()?.trim() || f.trim())
    .filter(Boolean);

  return (
    <>
      {/* 半透明遮罩 */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* SQL 抽屉主体 */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 rounded-t-2xl shadow-2xl animate-slide-up max-h-[70vh] flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-5 py-3 bg-slate-800 border-b border-slate-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            {/* macOS 窗口按钮 */}
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
            </div>
            <span className="text-sm text-slate-400 font-mono">DuckDB SQL Query</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "已复制" : "复制 SQL"}
            </button>
            <button
              onClick={onClose}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              关闭
            </button>
          </div>
        </div>

        {/* SQL 代码区（可滚动） */}
        <div className="flex-1 overflow-auto p-5">
          <pre
            className="text-sm font-mono leading-relaxed whitespace-pre"
            dangerouslySetInnerHTML={{ __html: highlightSql(sql) }}
          />
        </div>

        {/* 字段说明区 */}
        {fieldNames.length > 0 && (
          <div className="px-5 py-3 bg-slate-800 border-t border-slate-700 flex-shrink-0">
            <div className="flex items-center gap-1.5 mb-2">
              <Info className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-xs font-medium text-slate-400">字段说明</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {fieldNames.map((field: string) => (
                <span key={field} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-700 rounded-md text-xs">
                  <span className="font-mono text-blue-400">{field}</span>
                  <span className="text-slate-400">=</span>
                  <span className="text-emerald-400">{getFieldExplanation(field)}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 安全说明 */}
        <div className="px-5 py-2.5 bg-slate-800 border-t border-slate-700 flex-shrink-0">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded font-medium">安全</span>
            此 SQL 已通过 AST 只读安全检查，仅执行 SELECT/WITH 查询，数据无法被修改或删除。
          </div>
        </div>
      </div>

      {/* 全局样式（嵌入在组件内避免冲突） */}
      <style jsx global>{`
        .sql-string { color: #f472b6; }
        .sql-number { color: #fb923c; }
        .sql-keyword { color: #60a5fa; font-weight: 600; }
        .sql-comment { color: #6b7280; font-style: italic; }
      `}</style>
    </>
  );
}
