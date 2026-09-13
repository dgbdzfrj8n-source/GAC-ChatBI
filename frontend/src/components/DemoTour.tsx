'use client';

import { useEffect, useState, useCallback } from 'react';

const STORAGE_KEY = 'gac-chatbi-tour-completed';

interface TourStep {
  id: string;
  title: string;
  description: string;
  icon: string;
  /** 选择器：data-tour=xxx；不填 = 全屏居中 */
  anchor?: string;
  /** 位置：top / bottom / center */
  position?: 'top' | 'bottom' | 'center' | 'right';
  /** 提示气泡位置（相对 anchor） */
  tooltipPlacement?: 'top' | 'bottom' | 'left' | 'right' | 'center';
  highlight?: string;
  cta?: string;
}

const STEPS: TourStep[] = [
  {
    id: 'welcome',
    title: '欢迎使用广汽云 ChatBI',
    description:
      '4 大核心能力：🚗 整车销售分析 · 💰 经营财务透视 · 📣 营销渠道归因 · 🔍 智能驾驶舱大屏。\n\n这是 AI 产品经理视角的「自然语言问数」平台——业务人员用中文提问，AI 自动生成 SQL、图表与归因洞察。',
    icon: '👋',
    position: 'center',
  },
  {
    id: 'sidebar',
    title: '左侧导航 — 三大业务域',
    description:
      '导航按业务域组织：\n\n• 智能经营分析（智能对话 / 驾驶舱 / 报表）\n• 业务资产（指标库 / 数据表 / 历史会话 / 语义层）\n• 系统（设置 / 帮助）',
    icon: '🗂️',
    anchor: 'menu-group-analysis',
    tooltipPlacement: 'right',
    cta: '下一步带你看核心能力',
  },
  {
    id: 'chat-input',
    title: '自然语言问数',
    description:
      '在底部输入框直接问"广汽埃安3月销量达成率"——AI 会自动：\n\n1️⃣ Schema 剪枝（只查相关表，省 Token）\n2️⃣ NL2SQL 生成 DuckDB 安全 SQL\n3️⃣ ECharts 自适应图表 + 经营洞察',
    icon: '💬',
    anchor: 'chat-input',
    tooltipPlacement: 'top',
  },
  {
    id: 'sop',
    title: '深度归因 SOP（简历亮点）',
    description:
      '当销量波动时，点击工具栏的「深度归因」按钮触发四步下钻 SOP：\n\n📊 大盘对标 → 🎯 维度下钻 → 🔗 跨域归因 → 💡 策略建议\n\n无需 SQL，自动产出高管可读的归因报告。',
    icon: '🔍',
    anchor: 'sop-button',
    tooltipPlacement: 'bottom',
  },
  {
    id: 'dashboard',
    title: '驾驶舱大屏',
    description:
      '点击侧边栏「驾驶舱大屏」看 4 个 KPI + 趋势图 + 排名 + 预警，一屏掌控。\n\n所有图表基于 ECharts，支持深色主题。',
    icon: '🚗',
    anchor: 'menu-item-dashboard',
    tooltipPlacement: 'right',
  },
  {
    id: 'notification',
    title: '通知中心 🔔',
    description:
      '顶部铃铛按角色推送实时消息：\n\n🚨 KPI 异常预警 · 🔍 归因完成 · 📉 预算偏差 · ⚙️ 系统升级\n\n未读数小红点提醒，类型筛选 chip 切换，下拉时间线样式。',
    icon: '🔔',
    anchor: 'notification-bell',
    tooltipPlacement: 'bottom',
    cta: '下一步看语义层',
  },
  {
    id: 'semantic',
    title: '语义层管理（AI PM 加分项）',
    description:
      '点击侧边栏「语义层」管理 NL2SQL 的召回口径：\n\n📐 指标层 6 项（口径 / 公式 / 示例 SQL 可改）\n🧩 维度层 21 字段（自动从 schema 抽取）\n📖 同义词层 9 项（业务术语与别名）\n\n改动后立即生效，无需重新部署。',
    icon: '🧠',
    anchor: 'menu-item-semantic',
    tooltipPlacement: 'right',
  },
  {
    id: 'finish',
    title: '开始体验吧！',
    description:
      '推荐先试这 3 个高频问句：',
    icon: '🎉',
    position: 'center',
    cta: '完成引导',
  },
];

const SAMPLE_QUERIES = [
  { label: '🚗 销量达成', query: '广汽埃安 2025年3月销量与预算达成率是多少？' },
  { label: '📣 CPL 排名', query: '各营销渠道获客成本 CPL 排名' },
  { label: '🔍 深度归因', query: '为什么广汽传祺 2025-03 销量比预算差这么多？' },
];

export default function DemoTour() {
  const [active, setActive] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);
  const [highlightRect, setHighlightRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  // 启动条件：首次访问 或 用户手动触发
  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      // 延迟 800ms 让首屏渲染完毕再弹出，体验更顺
      const t = setTimeout(() => setActive(true), 800);
      return () => clearTimeout(t);
    }
  }, []);

  // 监听手动触发（来自 TopBar 按钮 / 帮助中心）
  useEffect(() => {
    function onTrigger() {
      setStepIdx(0);
      setActive(true);
    }
    window.addEventListener('gac-tour-start', onTrigger);
    return () => window.removeEventListener('gac-tour-start', onTrigger);
  }, []);

  // 计算锚点位置
  useEffect(() => {
    if (!active) {
      setHighlightRect(null);
      return;
    }
    const step = STEPS[stepIdx];
    if (!step.anchor) {
      setHighlightRect(null);
      return;
    }
    const el = document.querySelector(`[data-tour="${step.anchor}"]`) as HTMLElement | null;
    if (!el) {
      setHighlightRect(null);
      return;
    }
    // 滚动到可见
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const update = () => {
      const r = el.getBoundingClientRect();
      setHighlightRect({
        x: r.left - 8,
        y: r.top - 8,
        w: r.width + 16,
        h: r.height + 16,
      });
    };
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update);
    };
  }, [active, stepIdx]);

  const close = useCallback((markDone = true) => {
    setActive(false);
    if (markDone) localStorage.setItem(STORAGE_KEY, '1');
  }, []);

  const next = useCallback(() => {
    if (stepIdx >= STEPS.length - 1) {
      close(true);
      return;
    }
    setStepIdx((i) => i + 1);
  }, [stepIdx, close]);

  const prev = useCallback(() => {
    if (stepIdx === 0) return;
    setStepIdx((i) => i - 1);
  }, [stepIdx]);

  // 键盘快捷键
  useEffect(() => {
    if (!active) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close(false);
      else if (e.key === 'ArrowRight') next();
      else if (e.key === 'ArrowLeft') prev();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [active, next, prev, close]);

  if (!active) return null;

  const step = STEPS[stepIdx];
  const isCenter = step.tooltipPlacement === 'center' || !step.anchor;

  return (
    <div className="fixed inset-0 z-[9999]" aria-modal="true" role="dialog">
      {/* 遮罩层 + 高亮镂空 */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden="true">
        <defs>
          <mask id="tour-mask">
            <rect width="100%" height="100%" fill="white" />
            {highlightRect && (
              <rect
                x={highlightRect.x}
                y={highlightRect.y}
                width={highlightRect.w}
                height={highlightRect.h}
                rx="12"
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect width="100%" height="100%" fill="rgba(0,0,0,0.65)" mask="url(#tour-mask)" />
        {highlightRect && (
          <rect
            x={highlightRect.x}
            y={highlightRect.y}
            width={highlightRect.w}
            height={highlightRect.h}
            rx="12"
            fill="none"
            stroke="#3b82f6"
            strokeWidth="3"
            className="tour-highlight-pulse"
          />
        )}
      </svg>

      {/* Tooltip 卡片 */}
      <Tooltip
        step={step}
        stepIdx={stepIdx}
        totalSteps={STEPS.length}
        isCenter={isCenter}
        highlightRect={highlightRect}
        onNext={next}
        onPrev={prev}
        onClose={() => close(false)}
        onFinish={() => close(true)}
      />
    </div>
  );
}

interface TooltipProps {
  step: TourStep;
  stepIdx: number;
  totalSteps: number;
  isCenter: boolean;
  highlightRect: { x: number; y: number; w: number; h: number } | null;
  onNext: () => void;
  onPrev: () => void;
  onClose: () => void;
  onFinish: () => void;
}

function Tooltip({ step, stepIdx, totalSteps, isCenter, highlightRect, onNext, onPrev, onClose, onFinish }: TooltipProps) {
  // 计算 tooltip 位置
  const style: React.CSSProperties = isCenter
    ? {
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        position: 'fixed',
      }
    : calcTooltipStyle(step.tooltipPlacement || 'right', highlightRect);

  const isLast = stepIdx === totalSteps - 1;
  const progress = ((stepIdx + 1) / totalSteps) * 100;

  return (
    <div
      className="tour-tooltip bg-white dark:bg-gac-gray-900 rounded-2xl shadow-2xl border border-gac-gray-200 dark:border-gac-gray-700"
      style={{ ...style, width: '420px', maxWidth: 'calc(100vw - 32px)', zIndex: 10000 }}
    >
      {/* 进度条 */}
      <div className="h-1 bg-gac-gray-100 dark:bg-gac-gray-800 rounded-t-2xl overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="p-6">
        {/* 标题 */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{step.icon}</span>
            <h3 className="text-base font-semibold text-gac-gray-900 dark:text-white">
              {step.title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gac-gray-400 hover:text-gac-gray-600 text-lg leading-none w-6 h-6 flex items-center justify-center"
            aria-label="关闭引导"
          >
            ✕
          </button>
        </div>

        {/* 描述 */}
        <p className="text-sm text-gac-gray-600 dark:text-gac-gray-300 leading-relaxed whitespace-pre-line mb-4">
          {step.description}
        </p>

        {/* 最后一步：示例问句卡片 */}
        {step.id === 'finish' && (
          <div className="space-y-2 mb-4">
            {SAMPLE_QUERIES.map((s, i) => (
              <button
                key={i}
                onClick={() => {
                  // 跳转首页 + 填入问句
                  localStorage.setItem('gac-tour-pending-query', s.query);
                  window.location.href = '/';
                }}
                className="w-full text-left p-3 bg-gac-gray-50 dark:bg-gac-gray-800 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg border border-gac-gray-200 dark:border-gac-gray-700 transition-colors group"
              >
                <div className="text-xs font-medium text-gac-gray-900 dark:text-white mb-1">
                  {s.label}
                </div>
                <div className="text-xs text-gac-gray-600 dark:text-gac-gray-400 font-mono group-hover:text-blue-600">
                  {s.query}
                </div>
              </button>
            ))}
          </div>
        )}

        {/* 底部按钮组 */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-gac-gray-500">
            {stepIdx + 1} / {totalSteps}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-sm text-gac-gray-600 hover:text-gac-gray-900 hover:bg-gac-gray-100 dark:hover:bg-gac-gray-800 rounded-lg transition-colors"
            >
              跳过
            </button>
            {stepIdx > 0 && (
              <button
                onClick={onPrev}
                className="px-3 py-1.5 text-sm border border-gac-gray-200 dark:border-gac-gray-700 hover:bg-gac-gray-50 dark:hover:bg-gac-gray-800 text-gac-gray-700 dark:text-gac-gray-300 rounded-lg transition-colors"
              >
                上一步
              </button>
            )}
            <button
              onClick={isLast ? onFinish : onNext}
              className="px-4 py-1.5 text-sm font-medium bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white rounded-lg shadow-sm transition-all"
            >
              {isLast ? (step.cta || '完成') : step.cta || '下一步'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function calcTooltipStyle(
  placement: string,
  rect: { x: number; y: number; w: number; h: number } | null
): React.CSSProperties {
  if (!rect) return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)', position: 'fixed' };
  const gap = 16;
  const base: React.CSSProperties = { position: 'fixed' };
  switch (placement) {
    case 'top':
      return {
        ...base,
        left: Math.max(16, Math.min(window.innerWidth - 436, rect.x + rect.w / 2 - 210)),
        top: Math.max(16, rect.y - 240 - gap),
      };
    case 'bottom':
      return {
        ...base,
        left: Math.max(16, Math.min(window.innerWidth - 436, rect.x + rect.w / 2 - 210)),
        top: rect.y + rect.h + gap,
      };
    case 'left':
      return {
        ...base,
        left: Math.max(16, rect.x - 436 - gap),
        top: rect.y + rect.h / 2 - 140,
      };
    case 'right':
    default:
      return {
        ...base,
        left: rect.x + rect.w + gap,
        top: Math.max(16, Math.min(window.innerHeight - 320, rect.y + rect.h / 2 - 140)),
      };
  }
}
