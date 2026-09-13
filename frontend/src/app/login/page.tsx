"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface DemoAccount {
  username: string;
  name: string;
  role_label: string;
  scope: string;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://gac-chatbi.onrender.com";

export default function LoginPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<DemoAccount[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // 加载演示账号列表
  useEffect(() => {
    fetch(`${API_BASE}/api/auth/demo-accounts`)
      .then((r) => r.json())
      .then((d) => setAccounts(d.accounts || []))
      .catch(() => setAccounts([]));
  }, []);

  const handleLogin = async (u: string, p: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "登录失败");
      }
      const data = await res.json();
      localStorage.setItem("gac_chatbi_token", data.access_token);
      localStorage.setItem("gac_chatbi_user", JSON.stringify(data.user));
      router.push("/");
    } catch (e: any) {
      setError(e.message || "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-blue-50 flex items-center justify-center px-4">
      <div className="max-w-2xl w-full">
        {/* Logo + 标题 */}
        <div className="text-center mb-8">
          <div className="text-6xl mb-3">🚗</div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">广汽云 ChatBI</h1>
          <p className="text-gray-500 text-sm">Sprint 10：IAM 接入演示版 · 角色权限管理</p>
        </div>

        {/* 登录表单 */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">🔐 登录</h2>
          <div className="space-y-3">
            <input
              type="text"
              placeholder="用户名（演示版任意账号）"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <input
              type="password"
              placeholder="密码（演示版任意非空）"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              disabled={loading || !username || !password}
              onClick={() => handleLogin(username, password)}
              className="w-full py-2.5 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50 transition"
            >
              {loading ? "登录中..." : "登录"}
            </button>
            {error && (
              <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* 演示账号 */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-2">
            👥 演示账号（一键登录）
          </h3>
          <p className="text-xs text-gray-500 mb-4">
            生产环境会替换为广汽 IAM SSO 登录入口，本演示版直接点击下方账号体验不同角色权限差异。
          </p>
          <div className="space-y-2">
            {accounts.map((a) => (
              <button
                key={a.username}
                disabled={loading}
                onClick={() => handleLogin(a.username, "demo")}
                className="w-full flex items-center justify-between px-4 py-3 border border-gray-200 rounded-lg hover:bg-emerald-50 hover:border-emerald-300 transition text-left"
              >
                <div>
                  <div className="font-medium text-gray-800">
                    {a.name} <span className="text-xs text-gray-400 ml-1">@{a.username}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {a.role_label} · {a.scope}
                  </div>
                </div>
                <span className="text-emerald-600 text-sm font-medium">登录 →</span>
              </button>
            ))}
          </div>
        </div>

        {/* IAM 接入说明 */}
        <div className="mt-6 bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-800">
          <strong>📡 真实 IAM 接入路径</strong>：生产环境会接入广汽 IAM（OIDC 协议）。
          前端只需对接 <code className="bg-amber-100 px-1 rounded">/api/auth/oidc/callback</code>，
          其他代码完全不变。详情见 <code>GAC_CHATBI_IMPLEMENTATION_GUIDE.md</code>。
        </div>
      </div>
    </div>
  );
}
