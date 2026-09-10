"use client";

import { useState } from "react";
import { X, Copy, Check, Play } from "lucide-react";

interface SqlDrawerProps {
  sql: string;
  onClose: () => void;
}

// DuckDB/SQLite 语法高亮（简易 tokenizer）
function highlightSql(sql: string): string {
  const keywords = [
    "SELECT", "FROM", "WHERE", "JOIN", "ON", "GROUP", "BY", "ORDER", "ASC", "DESC",
    "HAVING", "LIMIT", "WITH", "AS", "AND", "OR", "NOT", "NULLIF", "ROUND", "SUM",
    "STRFTIME", "CASE", "WHEN", "THEN", "ELSE", "END", "IN", "LIKE", "BETWEEN",
    "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS", "UNION", "ALL",
  ];

  let result = sql
    // 转义 HTML
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // 字符串字面量（粉色）
    .replace(/'([^']*)'/g, "<span style='color:#f472b6'>'$1'</span>")
    // 数字字面量（橙色）
    .replace(/\b(\d+(?:\.\d+)?)\b/g, "<span style='color:#fb923c'>$1</span>")
    // 关键字（蓝色加粗）
    .replace(
      new RegExp(`\\b(${keywords.join("|")})\\b`, "gi"),
      "<span style='color:#3b82f6;font-weight:600'>$1</span>"
    );
  // 注释（灰色）
  result = result.replace(/(--[^\n]*)/g, "<span style='color:#9ca3af;font-style:italic'>$1</span>");

  return result;
}

export default function SqlDrawer({ sql, onClose }: SqlDrawerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-slate-900 rounded-xl overflow-hidden shadow-2xl animate-slide-up">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          <span className="text-xs text-slate-400 font-mono ml-2">DuckDB SQL Query</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? "已复制" : "复制"}
          </button>
          <button
            onClick={onClose}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            收起
          </button>
        </div>
      </div>

      {/* SQL 代码区 */}
      <div className="p-4 overflow-x-auto scrollbar-thin">
        <pre
          className="text-sm font-mono leading-relaxed whitespace-pre"
          dangerouslySetInnerHTML={{ __html: highlightSql(sql) }}
        />
      </div>

      {/* 底部说明 */}
      <div className="px-4 py-2.5 bg-slate-800 border-t border-slate-700 flex items-center gap-2">
        <Play className="w-3.5 h-3.5 text-emerald-400" />
        <span className="text-xs text-slate-400">
          此 SQL 已通过 AST 只读安全检查，仅执行 SELECT/WITH 查询，数据无法被修改或删除。
        </span>
      </div>
    </div>
  );
}
