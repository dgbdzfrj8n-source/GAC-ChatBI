/**
 * [Sprint 10] 前端鉴权工具
 *
 * 功能：
 *   1. Token 持久化（localStorage）
 *   2. 自动从 localStorage 读取用户信息
 *   3. fetch 包装：自动加 Authorization 头
 *   4. 401 自动跳登录页
 */

const TOKEN_KEY = "gac_chatbi_token";
const USER_KEY = "gac_chatbi_user";

export interface UserInfo {
  username: string;
  name: string;
  role: string;
  department: string;
  region: string;
  email: string;
  email_masked: string;
  phone: string;
  phone_masked: string;
}

export function setToken(token: string, user: UserInfo) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): UserInfo | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function logout() {
  clearAuth();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

/**
 * 鉴权版 fetch —— 自动加 Authorization 头，401 跳登录
 */
export async function authFetch(
  url: string,
  init: RequestInit = {}
): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && init.body && typeof init.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, { ...init, headers });

  if (res.status === 401) {
    // Token 失效，跳登录页
    clearAuth();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("未登录或登录已过期");
  }

  return res;
}
