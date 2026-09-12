'use client';

// 广汽集团品牌 Logo —— 竖版版（次选）
// 版式：银色 3D G 在上，红色 GAC 文字在下（viewBox 1024 × 724，宽高比 ≈ 1.414:1）
// 浅色主题使用 /brand/gac-logo-light.svg（内嵌高清 PNG，可任意缩放）
// 深色主题使用 /brand/gac-logo-dark.svg（暂用浅色版替代，后续可单独做深色版）
// 通过 <html class="dark"> 自动切换。
// size 仅控制高度，宽度按 viewBox 宽高比自动计算，绝不拉伸。

import { useEffect, useState } from 'react';

export type GacLogoSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | number;

interface GacLogoProps {
  size?: GacLogoSize;
  /** 是否随系统深色主题自动切换图片（默认 true） */
  autoTheme?: boolean;
  className?: string;
  /** 是否显示"广汽云 ChatBI"标题文字（仅竖版 logo 旁边） */
  showCaption?: boolean;
}

// 用 height 作为唯一尺寸基准（width 由 CSS 内部按 viewBox 宽高比自动算），避免任何拉伸
const HEIGHT_MAP: Record<Exclude<GacLogoSize, number>, number> = {
  xs: 28,
  sm: 36,
  md: 48,
  lg: 64,
  xl: 80,
};

function resolveHeight(size: GacLogoSize) {
  if (typeof size === 'number') return size;
  return HEIGHT_MAP[size];
}

export default function GacLogo({
  size = 'md',
  autoTheme = true,
  className = '',
  showCaption = false,
}: GacLogoProps) {
  const h = resolveHeight(size);
  const [isDark, setIsDark] = useState(false);
  const [bust, setBust] = useState('');

  useEffect(() => {
    if (!autoTheme) return;
    const root = document.documentElement;
    const sync = () => setIsDark(root.classList.contains('dark'));
    sync();
    const obs = new MutationObserver(sync);
    obs.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => obs.disconnect();
  }, [autoTheme]);

  // 破 CDN / 浏览器缓存：每次挂载加一个 v= 戳。
  useEffect(() => {
    setBust(`?v=${Date.now()}`);
  }, []);

  // 竖版 logo：浅色版用 SVG（包含内嵌 PNG），深色版先用同一张（业务上 sidebar 默认浅色）。
  // 未来如果要做深色专版，把 gac-logo-dark.svg 也准备好就行，组件无需改动。
  const lightSrc = `/brand/gac-logo-light.svg${bust}`;
  const darkSrc = `/brand/gac-logo-dark.svg${bust}`;

  const logoEl = (
    <img
      src={autoTheme && isDark ? darkSrc : lightSrc}
      alt="广汽集团 GAC"
      // ⚠️ 只锁 height，width 由 CSS 内部按 viewBox 宽高比自动算，避免任何拉伸变形
      height={h}
      className={`block flex-shrink-0 select-none ${className}`}
      style={{ height: `${h}px`, width: 'auto', maxWidth: 'none' }}
      draggable={false}
    />
  );

  if (!showCaption) return logoEl;

  return (
    <div className="flex items-center gap-3">
      {logoEl}
      <div className="flex flex-col leading-tight">
        <span className="text-[15px] font-semibold tracking-wide text-slate-900 dark:text-slate-50">
          广汽云 ChatBI
        </span>
        <span className="text-[10px] uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
          GAC Intelligent BI
        </span>
      </div>
    </div>
  );
}
