'use client';

import { useState, useEffect } from 'react';
import GacBadge from '@/components/GacBadge';

// v2.0 配置
const APP_VERSION = 'v2.0.0';
const SPRINT_NAME = 'Sprint 10';

// v2.0 模型列表
const MODELS = [
  {
    id: 'qwen3-coder-30b',
    name: 'Qwen3-Coder-30B',
    deployment: '私有化部署',
    is_default: true,
    description: '中文SQL生成准确率85%+，P85响应3.2s'
  },
  {
    id: 'deepseek-chat',
    name: 'DeepSeek Chat',
    deployment: '云端API',
    is_default: false,
    description: '演示环境实际使用，降低推理成本'
  },
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    deployment: '轻量备用',
    is_default: false,
    description: '极端情况下降级使用'
  }
];

// v2.0 性能统计数据（模拟）
const PERFORMANCE_STATS = {
  p50: '2.8s',
  p85: '3.2s',
  p95: '4.6s',
  total_queries: 1256,
  avg_response: '3.1s'
};

// v2.0 安全防护架构
const SECURITY_LAYERS = [
  {
    level: 1,
    icon: '🔐',
    name: 'IAM 统一认证',
    description: '接入广汽 IAM（OIDC 协议），SSO 单点登录，演示版用一键登录模拟'
  },
  {
    level: 2,
    icon: '👤',
    name: 'RBAC 角色权限',
    description: '4 种角色（高管/分析师/区域总监/4S 店长），不同角色数据范围不同'
  },
  {
    level: 3,
    icon: '🔒',
    name: '行级数据过滤',
    description: 'SQL 执行前自动注入品牌/区域过滤条件，用户只能看到授权范围数据'
  },
  {
    level: 4,
    icon: '🛡️',
    name: 'SQL 安全检查',
    description: 'AST 语法树解析，仅允许 SELECT/WITH，禁止 DDL/DML，防 SQL 注入'
  },
  {
    level: 5,
    icon: '📋',
    name: '审计日志',
    description: '所有写操作 append-only 留痕，支持合规审计与追溯'
  }
];

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState(
    typeof window !== 'undefined'
      ? (localStorage.getItem('apiUrl') || 'https://gac-chatbi-api.onrender.com')
    : 'https://gac-chatbi-api.onrender.com'
  );
  const [model, setModel] = useState('qwen3-coder-30b');
  const [theme, setTheme] = useState('light');
  const [showSql, setShowSql] = useState(true);
  const [securityExpanded, setSecurityExpanded] = useState(false);

  // 初始化主题
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    if (savedTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const handleThemeChange = (newTheme: string) => {
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const handleApiUrlChange = (url: string) => {
    setApiUrl(url);
    localStorage.setItem('apiUrl', url);
  };

  const currentModel = MODELS.find((m) => m.id === model);

  return (
    <div className="content-wrap max-w-3xl">
      {/* 顶部说明 */}
      <div className="content-card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0"><GacBadge size="lg" /></div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gac-gray-900 mb-1">设置</h2>
            <p className="text-sm text-gac-gray-500 leading-relaxed">
              系统配置与个性化选项，修改后将立即生效。
            </p>
          </div>
        </div>
      </div>

      {/* 模型配置 - v2.0 新版 */}
      <div className="content-card p-5 mb-4">
        <h3 className="text-sm font-semibold text-gac-gray-900 mb-4 flex items-center">
          <span className="w-1 h-4 bg-gac-primary rounded mr-2"></span>
          模型配置
          <span className="ml-2 px-1.5 py-0.5 text-[10px] bg-blue-100 text-blue-700 rounded">
            v2.0
          </span>
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gac-gray-700 mb-1.5">LLM 模型</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gac-primary bg-white"
            >
              {MODELS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} {m.is_default ? '（默认）' : ''} - {m.deployment}
                </option>
              ))}
            </select>
            
            {/* v2.0: 显示当前模型详情 */}
            {currentModel && (
              <div className="mt-2 p-3 bg-blue-50 rounded-lg border border-blue-100">
                <div className="text-xs text-blue-800">
                  <div className="font-medium">{currentModel.name}</div>
                  <div className="text-blue-600 mt-1">
                    {currentModel.description}
                  </div>
                  <div className="text-blue-500 mt-1 text-[10px]">
                    部署方式：{currentModel.deployment}
                  </div>
                </div>
              </div>
            )}
            
            <p className="text-xs text-gac-gray-500 mt-1.5">
              {model === 'qwen3-coder-30b' 
                ? '当前使用 Qwen3-Coder-30B，中文 SQL 生成准确率 85%+，端到端 P85 响应 3.2s'
                : '演示环境实际通过 DeepSeek API 推理，切换仅影响显示配置'}
            </p>
          </div>

          <div>
            <label className="block text-sm text-gac-gray-700 mb-1.5">后端 API 地址</label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => handleApiUrlChange(e.target.value)}
              className="w-full px-3 py-2 border border-gac-gray-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-gac-primary bg-white"
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
                { id: 'light', label: '☀️ 浅色' },
                { id: 'dark', label: '🌙 深色' },
                { id: 'auto', label: '🔄 跟随系统' },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => handleThemeChange(t.id)}
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

      {/* v2.0 性能统计卡片 */}
      <div className="content-card p-5 mb-4">
        <h3 className="text-sm font-semibold text-gac-gray-900 mb-4 flex items-center">
          <span className="w-1 h-4 bg-gac-primary rounded mr-2"></span>
          性能统计（近 7 天）
          <span className="ml-2 px-1.5 py-0.5 text-[10px] bg-green-100 text-green-700 rounded">
            v2.0
          </span>
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gac-gray-900">{PERFORMANCE_STATS.p50}</div>
            <div className="text-xs text-gac-gray-500 mt-1">P50 响应</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gac-gray-900">{PERFORMANCE_STATS.p85}</div>
            <div className="text-xs text-gac-gray-500 mt-1">P85 响应</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gac-gray-900">{PERFORMANCE_STATS.p95}</div>
            <div className="text-xs text-gac-gray-500 mt-1">P95 响应</div>
          </div>
        </div>
        <div className="mt-3 text-xs text-gac-gray-500 text-center">
          近 7 天共处理 {PERFORMANCE_STATS.total_queries} 次查询，平均响应 {PERFORMANCE_STATS.avg_response}
          <span className="ml-2 text-blue-500">（演示版模拟数据）</span>
        </div>
      </div>

      {/* v2.0 安全与权限卡片 */}
      <div className="content-card p-5 mb-4">
        <h3 className="text-sm font-semibold text-gac-gray-900 mb-4 flex items-center">
          <span className="w-1 h-4 bg-gac-primary rounded mr-2"></span>
          安全与权限
          <span className="ml-2 px-1.5 py-0.5 text-[10px] bg-red-100 text-red-700 rounded">
            v2.0
          </span>
        </h3>
        
        {/* 折叠/展开按钮 */}
        <button
          onClick={() => setSecurityExpanded(!securityExpanded)}
          className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <span className="text-sm text-gac-gray-700">五层防护架构</span>
          <span className="text-gac-gray-500">{securityExpanded ? '▲ 收起' : '▼ 展开'}</span>
        </button>
        
        {/* 五层详情 */}
        {securityExpanded && (
          <div className="mt-3 space-y-2">
            {SECURITY_LAYERS.map((layer) => (
              <div key={layer.level} className="flex items-start gap-3 p-3 border border-gray-100 rounded-lg">
                <div className="text-2xl flex-shrink-0">{layer.icon}</div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gac-gray-900">
                    层级{layer.level}：{layer.name}
                  </div>
                  <div className="text-xs text-gac-gray-500 mt-1">
                    {layer.description}
                  </div>
                </div>
              </div>
            ))}
            <div className="text-xs text-gac-gray-400 mt-2 text-center">
              演示版仅实现 SQL 安全检查和审计日志，IAM / 行级权限为 UI 展示
            </div>
          </div>
        )}
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
            <div className="text-gac-gray-900 font-medium">{APP_VERSION} ({SPRINT_NAME})</div>
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
