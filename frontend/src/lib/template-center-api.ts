// 归因模板中心 v3 - 前端 API 客户端
// 所有方法返回 Promise，错误抛出由调用方处理
import type {
  Template,
  TemplateVersion,
  TemplateRun,
  StepExecution,
  StepType,
  TemplateCategory,
  RunStatus,
  StepStatus,
} from "./template-center-types";

// 后端基地址
// 1) 优先：构建期注入（NEXT_PUBLIC_API_URL）
// 2) 兜底：写死 Render 后端域名（避免环境变量漏配导致前端 fetch 同源失败）
// 3) 最后：相对路径（本地 dev 用）
const RENDER_BACKEND = "https://gac-chatbi-api.onrender.com";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" &&
   window.location.hostname === "gac-chat-bi.onrender.com"
    ? RENDER_BACKEND
    : "") ||
  "";

export interface ListTemplatesParams {
  category?: string;
  keyword?: string;
  include_archived?: boolean;
  limit?: number;
  offset?: number;
}

export interface CreateTemplateBody {
  name: string;
  code: string;
  description: string;
  category: string;
  tags: string[];
  steps: any[];
}

export interface UpdateTemplateBody {
  name?: string;
  description?: string;
  category?: string;
  tags?: string[];
}

export interface PublishVersionBody {
  steps: any[];
  changelog: string;
}

export interface CreateRunBody {
  user_query: string;
  params: Record<string, any>;
}

// ---- HTTP 包装 ----
async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("gac_token") : null;
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers || {}),
      },
    });
    if (!res.ok) {
      const text = await res.text();
      let detail = text;
      try {
        detail = JSON.parse(text).detail || text;
      } catch {}
      throw new Error(`${res.status} ${res.statusText}: ${detail}`);
    }
    return res.json() as Promise<T>;
  } catch (e: any) {
    // 浏览器 fetch 失败（DNS/CORS/网络），给个可读错误
    if (e?.name === "TypeError" && /fetch|Load failed/i.test(e?.message || "")) {
      throw new Error(
        `无法连接后端 ${API_BASE || "(同源)"}：${e.message}。请检查后端服务是否启动 / CORS 是否放行 / 反向代理是否正确。`,
      );
    }
    throw e;
  }
}

// ============================================================
// 1) 元数据
// ============================================================
export async function getHealth(): Promise<{
  status: string;
  v3_tables_present: string[];
}> {
  return http("/api/template-center/health");
}

export async function getCategories(): Promise<{ items: { value: string; label: string }[] }> {
  return http("/api/template-center/categories");
}

export async function getStepTypes(): Promise<{
  items: { value: StepType; label: string; description: string }[];
}> {
  return http("/api/template-center/step-types");
}

// ============================================================
// 2) 模板 CRUD
// ============================================================
export async function listTemplates(p: ListTemplatesParams = {}): Promise<{
  items: Template[];
  total: number;
}> {
  const qs = new URLSearchParams();
  if (p.category) qs.append("category", p.category);
  if (p.keyword) qs.append("keyword", p.keyword);
  if (p.include_archived) qs.append("include_archived", "true");
  if (p.limit) qs.append("limit", String(p.limit));
  if (p.offset) qs.append("offset", String(p.offset));
  const suffix = qs.toString() ? `?${qs}` : "";
  return http(`/api/template-center/templates${suffix}`);
}

export async function getTemplate(id: string): Promise<Template> {
  return http(`/api/template-center/templates/${id}`);
}

export async function createTemplate(body: CreateTemplateBody): Promise<Template> {
  return http("/api/template-center/templates", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateTemplate(id: string, body: UpdateTemplateBody): Promise<Template> {
  return http(`/api/template-center/templates/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function archiveTemplate(id: string): Promise<{ template_id: string; archived: boolean }> {
  return http(`/api/template-center/templates/${id}`, { method: "DELETE" });
}

export async function publishNewVersion(
  id: string,
  body: PublishVersionBody,
): Promise<{ template_id: string; new_version: number }> {
  return http(`/api/template-center/templates/${id}/publish`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listTemplateVersions(id: string): Promise<{
  items: TemplateVersion[];
  total: number;
}> {
  return http(`/api/template-center/templates/${id}/versions`);
}

// ============================================================
// 3) 运行实例
// ============================================================
export async function createRun(
  templateId: string,
  body: CreateRunBody,
): Promise<{ run: TemplateRun; steps: StepExecution[] }> {
  return http(`/api/template-center/templates/${templateId}/runs`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listRuns(p: {
  template_id?: string;
  status?: RunStatus;
  limit?: number;
  offset?: number;
} = {}): Promise<{ items: TemplateRun[]; total: number }> {
  const qs = new URLSearchParams();
  if (p.template_id) qs.append("template_id", p.template_id);
  if (p.status) qs.append("status", p.status);
  if (p.limit) qs.append("limit", String(p.limit));
  if (p.offset) qs.append("offset", String(p.offset));
  const suffix = qs.toString() ? `?${qs}` : "";
  return http(`/api/template-center/runs${suffix}`);
}

export async function getRunDetail(runId: string): Promise<{
  run: TemplateRun;
  steps: StepExecution[];
}> {
  return http(`/api/template-center/runs/${runId}`);
}
