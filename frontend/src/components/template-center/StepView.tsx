"use client";

import { useState } from "react";
import { CheckCircle2, XCircle, Loader2, Clock, ChevronRight, ChevronDown } from "lucide-react";
import type { StepExecution, StepType, StepStatus } from "@/lib/template-center-types";
import { STEP_TYPE_LABEL, STEP_STATUS_COLOR } from "@/lib/template-center-types";

interface Props {
  steps: StepExecution[];
}

const STATUS_ICON: Record<
  StepStatus,
  (size: number) => JSX.Element
> = {
  pending: (s) => <Clock size={s} className="text-slate-400" />,
  running: (s) => <Loader2 size={s} className="text-blue-500 animate-spin" />,
  success: (s) => <CheckCircle2 size={s} className="text-emerald-500" />,
  failed: (s) => <XCircle size={s} className="text-rose-500" />,
  skipped: (s) => <Clock size={s} className="text-amber-500" />,
};

export default function StepView({ steps }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(
    () => new Set([0]), // 默认展开第 1 步
  );

  function toggle(idx: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  if (steps.length === 0) {
    return (
      <div className="text-center text-slate-400 py-8 text-sm">
        暂无执行步骤
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {steps.map((step, idx) => {
        const isOpen = expanded.has(idx);
        const Icon = STATUS_ICON[step.status as StepStatus];
        return (
          <div
            key={step.step_execution_id}
            className={`border-l-4 rounded-md border ${STEP_STATUS_COLOR[step.status as StepStatus]} transition`}
          >
            <button
              onClick={() => toggle(idx)}
              className="w-full flex items-center justify-between p-3 text-left"
            >
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-slate-500 w-6">
                  [{idx + 1}]
                </span>
                {Icon(18)}
                <div>
                  <div className="text-sm font-medium text-slate-900">
                    {step.step_name}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {STEP_TYPE_LABEL[step.step_type as StepType] || step.step_type}
                    {step.duration_ms != null && (
                      <span className="ml-2">⏱ {step.duration_ms}ms</span>
                    )}
                  </div>
                </div>
              </div>
              {isOpen ? (
                <ChevronDown size={18} className="text-slate-400" />
              ) : (
                <ChevronRight size={18} className="text-slate-400" />
              )}
            </button>
            {isOpen && (
              <div className="px-4 pb-4 space-y-3 border-t border-slate-200/50 pt-3">
                {step.error_message && (
                  <div className="p-2 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
                    ❌ {step.error_message}
                  </div>
                )}
                {step.input_data && Object.keys(step.input_data).length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-slate-600 mb-1">
                      📥 输入
                    </div>
                    <pre className="text-xs bg-slate-50 p-2 rounded border border-slate-200 overflow-x-auto max-h-48 overflow-y-auto">
                      {JSON.stringify(step.input_data, null, 2)}
                    </pre>
                  </div>
                )}
                {step.output_data != null && (
                  <div>
                    <div className="text-xs font-semibold text-slate-600 mb-1">
                      📤 输出
                    </div>
                    <pre className="text-xs bg-slate-50 p-2 rounded border border-slate-200 overflow-x-auto max-h-64 overflow-y-auto">
                      {JSON.stringify(step.output_data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
