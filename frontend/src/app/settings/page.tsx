'use client';

import { useState } from 'react';

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState(
    process.env.NEXT_PUBLIC_API_URL || 'https://gac-chatbi-api.onrender.com'
  );
  const [model, setModel] = useState('deepseek-chat');
  const [theme, setTheme] = useState('light');
  const [showSql, setShowSql] = useState(true);

  return (
    <div className="max-w-3xl">
      {/* 顶部说明 */}
      <div className="content-card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="gac-logo-lg">S</div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gac-gray-900 mb-1">设置</h2>
            <p className="text-sm text-gac-gray-500 leading-relaxed">
              系统配置与个性化选项，修改后将立即生效。
            </p>
          </div>
        </div>
      </div>

      {/* 模型配置 */}
      <div className="content-card p-5 mb-4">
        <h3 className="text-sm font-semibold text-gac-gray-900 mb-4 flex items-center">
          <span className="w-1 h-4 bg-gac-primary rounded mr-2"></span>
          模型配置
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gac-gray-700 mb-1.5">LLM 模型</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gac-primary"
            >
              <option value="deepseek-chat">DeepSeek Chat（推荐）</option>
              <option value="deepseek-reasoner">DeepSeek Reasoner（深度思考）</option>
              <option value="gpt-4o-mini">GPT-4o Mini（备用）</option>
            </select>
            <p className="text-xs text-gac-gray-500 mt-1.5">
              当前使用 DeepSeek Chat，速度与准确度平衡最佳。
            </p>
          </div>

          <div>
            <label className="block text-sm text-gac-gray-700 mb-1.5">后端 API 地址</label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-gac-primary"
            />
            <p className="text-xs text-gac-gray-500 mt-1.5">
              ⚠️ 修改后需要刷新页面才能生效。
            </p>
          </div>
        </div>
      </div>

      {/* 显示配置 */}
      <div className="content-card p-5 mb-4">
        <h3 className="text-sm font-semibold text-gac-gray-900 mb-4 flex items-center">
          <span className="w-1 h-4 bg-gac-primary rounded mr-2"></span>
          显示配置
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gac-gray-700 mb-2">主题</label>
            <div className="flex gap-2">
              {[
                { id: 'light', label: '☀️ 浅色', icon: '☀️' },
                { id: 'dark', label: '🌙 深色', icon: '🌙' },
                { id: 'auto', label: '🔄 跟随系统', icon: '🔄' },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTheme(t.id)}
                  className={
                    theme === t.id
                      ? 'btn-primary'
                      : 'px-4 py-2 bg-white text-gac-gray-700 border border-gac-gray-200 rounded-lg text-sm font-medium hover:bg-gac-gray-100'
                  }
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between py-2">
            <div>
              <div className="text-sm text-gac-gray-700">默认展开 SQL 代码</div>
              <div className="text-xs text-gac-gray-500 mt-0.5">查询结果同时显示底层 SQL</div>
            </div>
            <button
              onClick={() => setShowSql(!showSql)}
              className={
                showSql
                  ? 'w-11 h-6 bg-gac-primary rounded-full relative transition-colors'
                  : 'w-11 h-6 bg-gac-gray-300 rounded-full relative transition-colors'
              }
            >
              <span
                className={
                  showSql
                    ? 'absolute top-0.5 right-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-all'
                    : 'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-all'
                }
              ></span>
            </button>
          </div>
        </div>
      </div>

      {/* 关于 */}
      <div className="content-card p-5">
        <h3 className="text-sm font-semibold text-gac-gray-900 mb-4 flex items-center">
          <span className="w-1 h-4 bg-gac-primary rounded mr-2"></span>
          关于
        </h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gac-gray-500">产品名称</div>
            <div className="text-gac-gray-900 font-medium">广汽云 ChatBI</div>
          </div>
          <div>
            <div className="text-gac-gray-500">当前版本</div>
            <div className="text-gac-gray-900 font-medium">v1.7.0 (Sprint 7)</div>
          </div>
          <div>
            <div className="text-gac-gray-500">团队</div>
            <div className="text-gac-gray-900 font-medium">广汽集团 · 智能经营分析团队</div>
          </div>
          <div>
            <div className="text-gac-gray-500">技术栈</div>
            <div className="text-gac-gray-900 font-medium">Next.js 14 + FastAPI + DuckDB</div>
          </div>
        </div>
      </div>
    </div>
  );
}
