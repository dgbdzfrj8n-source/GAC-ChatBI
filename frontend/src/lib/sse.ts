/**
 * Sprint 5.1: SSE 流式客户端
 * 解析 text/event-stream 协议，逐事件 yield
 */

export interface StreamThoughtEvent {
  event: "thought";
  data: { step: number; text: string };
}

export interface StreamSqlEvent {
  event: "sql";
  data: { sql: string };
}

export interface StreamDataEvent {
  event: "data";
  data: {
    columns: string[];
    rows: Record<string, unknown>[];
    row_count: number;
    execution_time_ms: number;
  };
}

export interface StreamChartEvent {
  event: "chart";
  data: { chart_type: string; echarts_option: Record<string, unknown> };
}

export interface StreamInsightEvent {
  event: "insight";
  data: { text: string };
}

export interface StreamDoneEvent {
  event: "done";
  data: { success: boolean; healed: boolean; engine: string };
}

export interface StreamErrorEvent {
  event: "error";
  data: { error: string };
}

export interface StreamMetaAnswerEvent {
  event: "meta_answer";
  data: { text: string };
}

export type StreamEvent =
  | StreamThoughtEvent
  | StreamSqlEvent
  | StreamDataEvent
  | StreamChartEvent
  | StreamInsightEvent
  | StreamDoneEvent
  | StreamErrorEvent
  | StreamMetaAnswerEvent;

export interface StreamCallbacks {
  onThought?: (data: { step: number; text: string }) => void;
  onSql?: (data: { sql: string }) => void;
  onData?: (data: StreamDataEvent["data"]) => void;
  onChart?: (data: { chart_type: string; echarts_option: Record<string, unknown> }) => void;
  onInsight?: (text: string) => void;
  onInsightStart?: () => void;
  onDone?: (data: { success: boolean; healed: boolean; engine: string }) => void;
  onError?: (error: string) => void;
  onMetaAnswer?: (text: string) => void;
}

/**
 * 流式调用 /api/chat/stream
 * [FIX] 必须带 Authorization 头，否则后端返回 401，前端 catch 触发降级到 mock
 */
export async function streamChat(
  query: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://gac-chatbi-api.onrender.com";
  // 读取 token（不通过 authFetch，因为 SSE 流式响应需要直接拿到原始 ReadableStream）
  const token = typeof window !== "undefined" ? localStorage.getItem("gac_chatbi_token") : null;
  const res = await fetch(`${apiUrl}/api/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ query, force_mock: false }),
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = "";
    try {
      detail = await res.text();
    } catch {}
    // [P2 修复] 401 = token 过期，自动清登录态跳登录页（与 authFetch 行为一致）
    if (res.status === 401 && typeof window !== "undefined") {
      try {
        localStorage.removeItem("gac_chatbi_token");
        localStorage.removeItem("gac_chatbi_user");
      } catch {}
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    throw new Error(`HTTP ${res.status}${detail ? " · " + detail.slice(0, 120) : ""}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) continue;
      const eventMatch = line.match(/^event: (.+)\ndata: (.+)$/);
      if (!eventMatch) continue;

      const event = eventMatch[1];
      let data: any;
      try {
        data = JSON.parse(eventMatch[2]);
      } catch {
        continue;
      }

      switch (event) {
        case "thought":
          callbacks.onThought?.(data);
          break;
        case "sql":
          callbacks.onSql?.(data);
          break;
        case "data":
          callbacks.onData?.(data);
          break;
        case "chart":
          callbacks.onChart?.(data);
          break;
        case "insight":
          callbacks.onInsightStart?.();
          callbacks.onInsight?.(data.text);
          break;
        case "done":
          callbacks.onDone?.(data);
          break;
        case "error":
          callbacks.onError?.(data.error || "未知错误");
          break;
        case "meta_answer":
          callbacks.onMetaAnswer?.(data.text);
          break;
      }
    }
  }
}
