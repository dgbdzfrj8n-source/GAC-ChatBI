"use client";

import { useState } from "react";
import { getUser, logout, UserInfo } from "@/lib/auth";

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-red-100 text-red-700 border-red-200",
  analyst: "bg-blue-100 text-blue-700 border-blue-200",
  business_user: "bg-emerald-100 text-emerald-700 border-emerald-200",
  auditor: "bg-purple-100 text-purple-700 border-purple-200",
};

const ROLE_LABELS: Record<string, string> = {
  admin: "管理员",
  analyst: "分析师",
  business_user: "业务用户",
  auditor: "审计员",
};

export default function UserMenu() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [open, setOpen] = useState(false);

  // 客户端初始化读取
  if (typeof window !== "undefined" && !user) {
    const u = getUser();
    if (u) setUser(u);
  }

  if (!user) return null;

  const colorClass = ROLE_COLORS[user.role] || "bg-gray-100 text-gray-700";
  const label = ROLE_LABELS[user.role] || user.role;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-200 rounded-full hover:bg-gray-50 transition"
      >
        <div className="w-7 h-7 bg-gradient-to-br from-emerald-400 to-blue-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
          {user.name[0]}
        </div>
        <div className="text-left">
          <div className="text-xs font-medium text-gray-800">{user.name}</div>
        </div>
        <span className={`text-[10px] px-1.5 py-0.5 rounded border ${colorClass}`}>
          {label}
        </span>
      </button>

      {open && (
        <>
          {/* 点击外部关闭 */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
            {/* 用户信息 */}
            <div className="px-4 py-3 bg-gradient-to-br from-emerald-50 to-blue-50 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-emerald-400 to-blue-500 rounded-full flex items-center justify-center text-white text-base font-bold">
                  {user.name[0]}
                </div>
                <div>
                  <div className="font-semibold text-gray-800">{user.name}</div>
                  <div className="text-xs text-gray-500">@{user.username}</div>
                </div>
              </div>
              <div className="mt-2">
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${colorClass}`}>
                  {label}
                </span>
              </div>
            </div>

            {/* 权限范围 */}
            <div className="px-4 py-3 text-xs space-y-1.5 border-b border-gray-100">
              <div className="flex justify-between">
                <span className="text-gray-500">所属部门</span>
                <span className="text-gray-800 font-medium">{user.department}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">数据区域</span>
                <span className="text-gray-800 font-medium">{user.region === 'ALL' ? '全集团' : user.region}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">邮箱</span>
                <span className="text-gray-800 font-medium">{user.email_masked}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">手机</span>
                <span className="text-gray-800 font-medium">{user.phone_masked}</span>
              </div>
            </div>

            {/* 操作 */}
            <button
              onClick={() => {
                setOpen(false);
                logout();
              }}
              className="w-full px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50 transition flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              退出登录
            </button>
          </div>
        </>
      )}
    </div>
  );
}
