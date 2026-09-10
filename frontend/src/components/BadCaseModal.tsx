"use client";

import { useState } from "react";
import { X, AlertTriangle, CheckCircle } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface BadCaseModalProps {
  query: string;
  sql: string;
  onClose: () => void;
}

const FEEDBACK_TYPES = [
  { id: "calculation_error", label: "口径计算错误", desc: "指标计算结果与业务定义不符" },
  { id: "chart_mismatch", label: "图表类型不匹配", desc: "可视化效果无法清晰展示数据" },
  { id: "sql_syntax_error", label: "SQL 语法错误", desc: "执行时报 SQL 语法异常" },
  { id: "data_missing", label: "数据缺失", desc: "查询结果不完整或数据异常" },
  { id: "other", label: "其他问题", desc: "其他非预期行为" },
];

export default function BadCaseModal({ query, sql, onClose }: BadCaseModalProps) {
  const [selectedType, setSelectedType] = useState("");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!selectedType) return;
    setSubmitting(true);

    try {
      await fetch(`${API_URL}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          sql,
          feedback_type: selectedType,
          user_comment: comment,
        }),
      });
      setSubmitted(true);
      setTimeout(onClose, 1500);
    } catch {
      // 即使网络失败也关闭弹窗
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden animate-slide-up">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-red-50">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h3 className="font-semibold text-gray-900">反馈问题</h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {submitted ? (
          <div className="p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-emerald-500" />
            </div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">反馈已提交</h4>
            <p className="text-sm text-gray-500">感谢您的反馈，将帮助我们持续优化产品体验</p>
          </div>
        ) : (
          <>
            <div className="p-6 space-y-5">
              {/* 问题类型 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  请选择问题类型
                </label>
                <div className="grid grid-cols-1 gap-2">
                  {FEEDBACK_TYPES.map((type) => (
                    <button
                      key={type.id}
                      onClick={() => setSelectedType(type.id)}
                      className={`flex items-start gap-3 p-3 rounded-xl border text-left transition-all ${
                        selectedType === type.id
                          ? "border-red-300 bg-red-50 ring-1 ring-red-200"
                          : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                      }`}
                    >
                      <div
                        className={`w-4 h-4 mt-0.5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                          selectedType === type.id ? "border-red-500 bg-red-500" : "border-gray-300"
                        }`}
                      >
                        {selectedType === type.id && (
                          <div className="w-1.5 h-1.5 rounded-full bg-white" />
                        )}
                      </div>
                      <div>
                        <p className={`text-sm font-medium ${selectedType === type.id ? "text-red-700" : "text-gray-800"}`}>
                          {type.label}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">{type.desc}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* 补充说明 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  补充说明（选填）
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="请描述您期望的正确行为或改进建议..."
                  className="w-full resize-none rounded-xl border border-gray-200 px-3 py-2.5 text-sm
                             focus:outline-none focus:ring-2 focus:ring-red-300 focus:border-red-300
                             placeholder:text-gray-400"
                  rows={3}
                />
              </div>
            </div>

            {/* 底部按钮 */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-200 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={!selectedType || submitting}
                className="px-5 py-2 rounded-xl text-sm font-medium text-white bg-red-500 
                           hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed
                           transition-all active:scale-95"
              >
                {submitting ? "提交中..." : "提交反馈"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
