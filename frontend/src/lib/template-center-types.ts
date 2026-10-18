/**
 * 归因模板中心 v3 - TypeScript 类型
 * 与后端 Pydantic 模型对齐
 */

export type RunStatus = "pending" | "running" | "success" | "failed" | "cancelled";
export type StepStatus = "pending" | "running" | "success" | "failed" | "skipped";
export type StepType = "nl2sql" | "strategy" | "aggregation" | "conclusion" | "llm_direct";
export type VersionStatus = "draft" | "published";
export type TemplateCategory =
  | "销售归因"
  | "市场归因"
  | "库存归因"
  | "渠道归因"
  | "自定义";

export interface StepVariable {
  name: string;
  label: string;
  type: "string" | "number" | "date" | "select";
  required: boolean;
  default?: any;
  options?: string[];
}

export interface StepSpec {
  name: string;
  type: StepType;
  description?: string;
  question?: string;
  metrics?: string[];
  dimensions?: string[];
  strategy?: string;
  aggregation?: string;
  group_by?: string[];
  prompt?: string;
  variables: StepVariable[];
  depends_on?: string[];
}

export interface Template {
  template_id: string;
  name: string;
  code: string;
  description: string;
  category: string;
  tags: string[];
  current_version: number;
  is_archived: boolean;
  is_builtin: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TemplateVersion {
  template_id: string;
  version: number;
  steps: StepSpec[];
  status: VersionStatus;
  changelog: string;
  created_by: string;
  created_at: string;
}

export interface TemplateRun {
  run_id: string;
  template_id: string;
  template_version: number;
  user_query: string;
  params: Record<string, any>;
  status: RunStatus;
  total_steps: number;
  completed_steps: number;
  summary: any | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  created_by: string;
  created_at: string;
}

export interface StepExecution {
  step_execution_id: string;
  run_id: string;
  step_index: number;
  step_name: string;
  step_type: StepType;
  input_data: Record<string, any>;
  output_data: any | null;
  status: StepStatus;
  error_message: string | null;
  duration_ms: number | null;
  created_at: string;
}

// 步骤类型中文映射
export const STEP_TYPE_LABEL: Record<StepType, string> = {
  nl2sql: "自然语言查询",
  strategy: "策略选择",
  aggregation: "数据聚合",
  conclusion: "AI 结论",
  llm_direct: "LLM 直接推理",
};

export const RUN_STATUS_LABEL: Record<RunStatus, string> = {
  pending: "等待中",
  running: "执行中",
  success: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export const RUN_STATUS_COLOR: Record<RunStatus, string> = {
  pending: "bg-slate-100 text-slate-700",
  running: "bg-blue-100 text-blue-700",
  success: "bg-emerald-100 text-emerald-700",
  failed: "bg-rose-100 text-rose-700",
  cancelled: "bg-amber-100 text-amber-700",
};

export const STEP_STATUS_COLOR: Record<StepStatus, string> = {
  pending: "border-slate-300 bg-slate-50",
  running: "border-blue-400 bg-blue-50",
  success: "border-emerald-400 bg-emerald-50",
  failed: "border-rose-400 bg-rose-50",
  skipped: "border-amber-400 bg-amber-50",
};
