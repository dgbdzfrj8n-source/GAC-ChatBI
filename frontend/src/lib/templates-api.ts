/**
 * [P2-SprintB] SOP 步骤化模板 API Client
 *
 * 封装后端 v2 模板接口，自动注入 token，支持业务用户 + admin 双轨
 */

import { authFetch } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ──────────────────────────────────────────────────────────
// 类型定义
// ──────────────────────────────────────────────────────────
export type StepType =
  | "overall_kpi"
  | "yoy_compare"
  | "period_compare"
  | "horizontal_compare"
  | "drill_down"
  | "cross_attribution"
  | "anomaly_alert"
  | "strategy_recommend";

export interface StepSpec {
  step_id: string;
  title: string;
  step_type: StepType;
  metric_key: string;
  group_by: string[];
  compare_with?: Record<string, any> | null;
  compare_mode: "plan" | "yoy" | "mom" | "yoy_mom";
  compare_period?: string | null;
  threshold?: Record<string, number> | null;
  top_n?: number | null;
  depends_on?: string | null;
  order: number;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  scope: "system" | "role_default" | "market" | "user";
  owner_role?: string | null;
  owner_user?: string | null;
  metric_key?: string;
  dimensions: string[];
  steps: StepSpec[];
  created_at?: string | null;
  updated_at?: string | null;
  updated_by?: string | null;
}

export interface TemplateListResponse {
  system_presets: Template[];
  role_default_id: string | null;
  role_defaults_map: Record<string, string>;
  user_templates: Template[];
}

export interface SopStepReport {
  step_id: string;
  title: string;
  step_type: StepType;
  status: "ok" | "warn" | "bad" | "info";
  sql: string | null;
  conclusion: string;
  data: Record<string, any>[];
  columns: string[];
  row_count: number;
  metrics: Record<string, number>;
  execution_time_ms: number;
  engine?: string;
  error?: string | null;
  permission?: Record<string, any>;
  depends_on?: string | null;
}

export interface TemplateRunResponse {
  template_id: string;
  template_name: string;
  steps_count: number;
  steps_executed: number;
  report: SopStepReport[];
  executive_summary: string;
  total_execution_time_ms: number;
  is_preview?: boolean;
}

// ──────────────────────────────────────────────────────────
// 通用列表（兼容老接口）
// ──────────────────────────────────────────────────────────
export async function listTemplates(
  role?: string,
  user?: string
): Promise<TemplateListResponse> {
  const params = new URLSearchParams();
  if (role) params.set("role", role);
  if (user) params.set("user", user);
  const qs = params.toString();
  const url = `${API_URL}/api/sop/templates${qs ? "?" + qs : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`listTemplates failed: ${res.status}`);
  return res.json();
}

// ──────────────────────────────────────────────────────────
// V2 业务用户：CRUD + clone + audit
// ──────────────────────────────────────────────────────────
export async function v2CreateTemplate(req: {
  name: string;
  description?: string;
  steps: StepSpec[];
  change_reason?: string;
}): Promise<{ success: boolean; template: Template }> {
  const res = await authFetch(`${API_URL}/api/templates/v2/create`, {
    method: "POST",
    body: JSON.stringify({ scope: "user", ...req }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `create failed: ${res.status}`);
  }
  return res.json();
}

export async function v2UpdateTemplate(
  templateId: string,
  req: {
    name?: string;
    description?: string;
    steps?: StepSpec[];
    change_reason?: string;
  }
): Promise<{ success: boolean; template_id: string; template: Template }> {
  const res = await authFetch(
    `${API_URL}/api/templates/v2/${encodeURIComponent(templateId)}`,
    {
      method: "PUT",
      body: JSON.stringify(req),
    }
  );
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `update failed: ${res.status}`);
  }
  return res.json();
}

export async function v2DeleteTemplate(templateId: string): Promise<{ success: boolean }> {
  const res = await authFetch(
    `${API_URL}/api/templates/v2/${encodeURIComponent(templateId)}`,
    { method: "DELETE" }
  );
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `delete failed: ${res.status}`);
  }
  return res.json();
}

export async function v2CloneTemplate(req: {
  source_template_id: string;
  target_scope: "market" | "user";
  new_name?: string;
}): Promise<{ success: boolean; template: Template }> {
  const res = await authFetch(`${API_URL}/api/templates/v2/clone`, {
    method: "POST",
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `clone failed: ${res.status}`);
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────
// V2 业务用户：Run + Preview（核心端点）
// ──────────────────────────────────────────────────────────
export async function v2RunTemplate(
  templateId: string,
  req: {
    time_window?: { start: string; end: string };
    max_steps?: number;
    llm_conclusion?: boolean;
  } = {}
): Promise<TemplateRunResponse> {
  const res = await authFetch(
    `${API_URL}/api/templates/v2/${encodeURIComponent(templateId)}/run`,
    {
      method: "POST",
      body: JSON.stringify(req),
    }
  );
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `run failed: ${res.status}`);
  }
  return res.json();
}

export async function v2PreviewTemplate(
  templateId: string,
  req: {
    time_window?: { start: string; end: string };
    max_steps?: number;
  } = {}
): Promise<TemplateRunResponse> {
  const res = await authFetch(
    `${API_URL}/api/templates/v2/${encodeURIComponent(templateId)}/preview`,
    {
      method: "POST",
      body: JSON.stringify(req),
    }
  );
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `preview failed: ${res.status}`);
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────
// V2 业务用户：audit
// ──────────────────────────────────────────────────────────
export interface AuditItem {
  audit_id: string;
  template_id: string;
  version_no: number;
  snapshot: Record<string, any>;
  changed_by: string | null;
  change_reason: string | null;
  changed_at: string | null;
}
export async function v2GetAudit(
  templateId: string,
  limit = 10
): Promise<{ template_id: string; history: AuditItem[] }> {
  const res = await authFetch(
    `${API_URL}/api/templates/v2/${encodeURIComponent(templateId)}/audit?limit=${limit}`
  );
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `audit failed: ${res.status}`);
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────
// Admin：系统模板管理
// ──────────────────────────────────────────────────────────
export async function adminCreateTemplate(req: {
  name: string;
  description?: string;
  scope: "system" | "role_default" | "market" | "user";
  steps: StepSpec[];
  change_reason?: string;
}): Promise<{ success: boolean; template: Template }> {
  const res = await authFetch(`${API_URL}/api/admin/templates`, {
    method: "POST",
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `admin create failed: ${res.status}`);
  }
  return res.json();
}

export async function adminUpdateTemplate(
  templateId: string,
  req: {
    name?: string;
    description?: string;
    steps?: StepSpec[];
    change_reason?: string;
  }
): Promise<{ success: boolean; template_id: string; template: Template }> {
  const res = await authFetch(
    `${API_URL}/api/admin/templates/${encodeURIComponent(templateId)}`,
    {
      method: "PUT",
      body: JSON.stringify(req),
    }
  );
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `admin update failed: ${res.status}`);
  }
  return res.json();
}

export async function adminGetAudit(
  templateId: string,
  limit = 50
): Promise<{ template_id: string; history: AuditItem[] }> {
  const res = await authFetch(
    `${API_URL}/api/admin/templates/${encodeURIComponent(templateId)}/audit?limit=${limit}`
  );
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `admin audit failed: ${res.status}`);
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────
// 辅助：归因指标目录（兼容老接口）
// ──────────────────────────────────────────────────────────
export interface MetricOption {
  key: string;
  label: string;
  unit: string;
  description: string;
  applicable_dimensions: string[];
}
export async function listSupportedMetrics(): Promise<MetricOption[]> {
  const res = await fetch(`${API_URL}/api/sop/supported-metrics`);
  if (!res.ok) throw new Error(`metrics failed: ${res.status}`);
  const j = await res.json();
  return j.metrics || [];
}

// ──────────────────────────────────────────────────────────
// 单模板获取（兼容老接口，但返回完整 steps）
// ──────────────────────────────────────────────────────────
export async function getTemplate(templateId: string): Promise<Template | null> {
  const res = await fetch(
    `${API_URL}/api/sop/templates/${encodeURIComponent(templateId)}`
  );
  if (!res.ok) return null;
  const j = await res.json();
  return j.template || null;
}

// ──────────────────────────────────────────────────────────
// 业务工具：生成唯一 step_id（前端临时构造用，后端会校验）
// ──────────────────────────────────────────────────────────
let _seq = 0;
export function genStepId(): string {
  _seq++;
  return `step_${Date.now().toString(36)}_${_seq}`;
}

// ──────────────────────────────────────────────────────────
// 8 种 step_type 中文名 + 图标 + 默认配置
// ──────────────────────────────────────────────────────────
export const STEP_TYPE_META: Record<
  StepType,
  { label: string; icon: string; description: string; defaultMetric: string }
> = {
  overall_kpi: {
    label: "整体达成率",
    icon: "🎯",
    description: "计算整体达成率 vs 目标/同比/环比",
    defaultMetric: "delivered_units",
  },
  yoy_compare: {
    label: "YoY 同比",
    icon: "📈",
    description: "本期 vs 去年同期",
    defaultMetric: "delivered_units",
  },
  period_compare: {
    label: "环比/同期对比",
    icon: "📊",
    description: "本期 vs 上期",
    defaultMetric: "delivered_units",
  },
  horizontal_compare: {
    label: "横向对比",
    icon: "↔️",
    description: "多品牌/区域并列对比",
    defaultMetric: "delivered_units",
  },
  drill_down: {
    label: "下钻找异常",
    icon: "🔍",
    description: "按维度下钻找最薄弱项",
    defaultMetric: "delivered_units",
  },
  cross_attribution: {
    label: "跨域归因",
    icon: "🧩",
    description: "贡献度拆解",
    defaultMetric: "delivered_units",
  },
  anomaly_alert: {
    label: "异常告警",
    icon: "⚠️",
    description: "z-score 异常检测",
    defaultMetric: "delivered_units",
  },
  strategy_recommend: {
    label: "策略建议",
    icon: "💡",
    description: "基于上游 step 的可执行建议",
    defaultMetric: "delivered_units",
  },
};
