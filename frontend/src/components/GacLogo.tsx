'use client';

// 广汽集团品牌 Logo（PNG 图片版）
// 浅色主题使用 /brand/gac-logo-light.png
// 深色主题使用 /brand/gac-logo-dark.png
// 通过 <html class="dark"> 自动切换；可通过 tailwind 的 dark: 进一步样式控制。
// 保留 size 兼容旧调用（'sm' | 'md' | 'lg' | number），单位为高度 px（自动算宽度）。

import { useEffect, useState } from 'react';

export type GacLogoSize = 'sm' | 'md' | 'lg' | number;

interface GacLogoProps {
  size?: GacLogoSize;
  /** 是否随系统深色主题自动切换图片（默认 true） */
  autoTheme?: boolean;
  className?: string;
}

const SIZE_MAP: Record<Exclude<GacLogoSize, number>, { h: number; w: number }> = {
  sm: { h: 32, w: 60 },   // 偏宽，与「广汽云 ChatBI」并排
  md: { h: 38, w: 72 },
  lg: { h: 52, w: 96 },
};

function resolveSize(size: GacLogoSize) {
  if (typeof size === 'number') {
    return { h: size, w: Math.round(size * 1.85) };
  }
  return SIZE_MAP[size];
}

export default function GacLogo({
  size = 'md',
  autoTheme = true,
  className = '',
}: GacLogoProps) {
  const { h, w } = resolveSize(size);
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    if (!autoTheme) return;
    const root = document.documentElement;
    const sync = () => setIsDark(root.classList.contains('dark'));
    sync();
    // 监听 html class 变化（用户切换主题时）
    const obs = new MutationObserver(sync);
    obs.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => obs.disconnect();
  }, [autoTheme]);

  const lightSrc = '/brand/gac-logo-light.png';
  const darkSrc = '/brand/gac-logo-dark.png';

  return (
    <img
      src={autoTheme && isDark ? darkSrc : lightSrc}
      alt="广汽云 ChatBI"
      width={w}
      height={h}
      className={`block flex-shrink-0 select-none ${className}`}
      style={{ height: `${h}px`, width: `${w}px` }}
      draggable={false}
    />
  );
}
