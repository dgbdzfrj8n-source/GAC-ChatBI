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
 */
export async function streamChat(
  query: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const res = await fetch(`${apiUrl}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, force_mock: false }),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status}`);
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
