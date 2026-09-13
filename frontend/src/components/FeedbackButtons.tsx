'use client';

import { useState } from 'react';
import { useRole } from '@/contexts/RoleContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const FEEDBACK_LABELS: Record<string, { label: string; color: string; icon: string }[]> = {
  negative: [
    { label: 'SQL 错误', color: 'red', icon: '🐛' },
    { label: '口径偏差', color: 'orange', icon: '🎯' },
    { label: '数据缺失', color: 'amber', icon: '🕳️' },
    { label: '性能慢', color: 'blue', icon: '⏱️' },
    { label: '其他', color: 'gray', icon: '💬' },
  ],
  correction: [
    { label: '字段名修正', color: 'indigo', icon: '🔤' },
    { label: '口径修正', color: 'purple', icon: '🎯' },
    { label: '聚合方式', color: 'blue', icon: '📐' },
  ],
};

interface FeedbackButtonsProps {
  query: string;
  sql?: string;
  summary?: string;
  messageId?: string;
}

export default function FeedbackButtons({ query, sql, summary }: FeedbackButtonsProps) {
  const { role } = useRole();
  const [voted, setVoted] = useState<'positive' | 'negative' | 'correction' | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState('');
  const [correction, setCorrection] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // 只有 analyst / product 才能提交反馈
  const canSubmit = ['analyst', 'product'].includes(role);

  async function submitFeedback(feedback_type: 'positive' | 'negative' | 'correction') {
    if (!canSubmit) {
      alert('当前角色无反馈权限（仅分析师 / AI 产品经理可提交）');
      return;
    }
    setSubmitting(true);
    try {
      const body = {
        actor: role,
        query,
        sql_text: sql,
        result_summary: summary,
        feedback_type,
        feedback_label: selectedLabel || undefined,
        correction: correction || undefined,
      };
      const r = await fetch(`${API_URL}/api/bad-case/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (r.ok) {
        setSubmitted(true);
        setVoted(feedback_type);
        setShowForm(false);
        // 同时派发通知
        window.dispatchEvent(
          new CustomEvent('gac-notification', {
            detail: {
              type: feedback_type === 'positive' ? 'badcase_feedback' : 'system',
              severity: feedback_type === 'positive' ? 'success' : 'warning',
              title:
                feedback_type === 'positive'
                  ? '👍 你已采纳该回答，计入指标库'
                  : '👎 反馈已记录，将由 AI PM 复核',
              body:
                feedback_type === 'positive'
                  ? '采纳反馈有助于提升下次同类问数的准确度'
                  : `${selectedLabel ? `[${selectedLabel}] ` : ''}${correction || '请参考 SQL 修正'}`,
              link: '/semantic',
              audience: ['analyst', 'product'],
            },
          })
        );
      }
    } catch (e) {
      // 静默
    } finally {
      setSubmitting(false);
    }
  }

  if (!canSubmit) {
    return (
      <div className="text-[11px] text-gac-gray-400 mt-2 flex items-center gap-1">
        🔒 当前角色无反馈权限
      </div>
    );
  }

  if (submitted) {
    return (
      <div
        className={`mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium ${
          voted === 'positive'
            ? 'bg-emerald-50 text-emerald-700'
            : 'bg-orange-50 text-orange-700'
        }`}
      >
        {voted === 'positive' ? '👍 已采纳' : '👎 已记录 · 待 AI PM 复核'}
      </div>
    );
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2" data-tour="feedback-buttons">
      {!showForm ? (
        <>
          <button
            onClick={() => submitFeedback('positive')}
            disabled={submitting}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] bg-emerald-50 hover:bg-emerald-100 text-emerald-700 disabled:opacity-50 transition-colors"
            title="采纳该回答"
          >
            👍 采纳
          </button>
          <button
            onClick={() => setShowForm(true)}
            disabled={submitting}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] bg-orange-50 hover:bg-orange-100 text-orange-700 disabled:opacity-50 transition-colors"
            title="不采纳并反馈"
          >
            👎 不采纳
          </button>
          <button
            onClick={() => {
              setShowForm(true);
            }}
            disabled={submitting}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] bg-blue-50 hover:bg-blue-100 text-blue-700 disabled:opacity-50 transition-colors"
            title="修正口径"
          >
            📝 修正
          </button>
        </>
      ) : (
        <div className="w-full mt-2 p-3 bg-gac-gray-50 rounded-lg border border-gac-gray-200 dark:bg-gac-gray-800 dark:border-gac-gray-700">
          <div className="text-[11px] font-medium text-gac-gray-700 dark:text-gac-gray-300 mb-2">
            {voted === null ? '选择问题类型（可多选提示）' : '选择问题类型'}
          </div>
          <div className="flex flex-wrap gap-1.5 mb-2">
            {(FEEDBACK_LABELS.negative).map((l) => (
              <button
                key={l.label}
                onClick={() => setSelectedLabel(l.label)}
                className={`text-[11px] px-2 py-1 rounded-md border ${
                  selectedLabel === l.label
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white dark:bg-gac-gray-900 border-gac-gray-300 text-gac-gray-700 dark:text-gac-gray-300 hover:border-blue-300'
                }`}
              >
                {l.icon} {l.label}
              </button>
            ))}
          </div>
          <textarea
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
            placeholder="可选：输入正确口径或修正建议（将用于改进下次问数）"
            rows={2}
            className="w-full px-2 py-1.5 text-xs rounded-md border border-gac-gray-300 dark:border-gac-gray-600 bg-white dark:bg-gac-gray-900 text-gac-gray-900 dark:text-white focus:outline-none focus:border-blue-500 resize-none"
          />
          <div className="flex items-center gap-2 mt-2">
            <button
              onClick={() => submitFeedback('negative')}
              disabled={submitting}
              className="text-[11px] px-3 py-1.5 rounded-md bg-orange-600 text-white hover:bg-orange-700 disabled:opacity-50"
            >
              {submitting ? '提交中…' : '提交反馈'}
            </button>
            <button
              onClick={() => {
                setShowForm(false);
                setSelectedLabel('');
                setCorrection('');
              }}
              className="text-[11px] px-3 py-1.5 rounded-md text-gac-gray-600 hover:bg-gac-gray-200"
            >
              取消
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
