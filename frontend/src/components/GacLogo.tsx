'use client';

// 广汽集团品牌 Logo（PNG 图片版）
// 浅色主题使用 /brand/gac-logo-light.png
// 深色主题使用 /brand/gac-logo-dark.png
// 通过 <html class="dark"> 自动切换。
// size 仅控制高度，宽度按图片原始宽高比 (1024:837 ≈ 1.223:1) 自动计算，绝不拉伸。

import { useEffect, useState } from 'react';

export type GacLogoSize = 'sm' | 'md' | 'lg' | number;

interface GacLogoProps {
  size?: GacLogoSize;
  /** 是否随系统深色主题自动切换图片（默认 true） */
  autoTheme?: boolean;
  className?: string;
}

// 原始 PNG 宽高比（1024 × 837），保留比例的关键
const ASPECT = 1024 / 837;
// 用 height 作为唯一尺寸基准（width 由 CSS 内部按比例算），避免任何拉伸
const HEIGHT_MAP: Record<Exclude<GacLogoSize, number>, number> = {
  sm: 24,
  md: 30,
  lg: 40,
};

function resolveHeight(size: GacLogoSize) {
  if (typeof size === 'number') return size;
  return HEIGHT_MAP[size];
}

export default function GacLogo({
  size = 'md',
  autoTheme = true,
  className = '',
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
  // 部署/刷新页面后保证浏览器拿到的是最新抠过色的 PNG。
  useEffect(() => {
    setBust(`?v=${Date.now()}`);
  }, []);

  const lightSrc = `/brand/gac-logo-light.png${bust}`;
  const darkSrc = `/brand/gac-logo-dark.png${bust}`;

  return (
    <img
      src={autoTheme && isDark ? darkSrc : lightSrc}
      alt="广汽云 ChatBI"
      // ⚠️ 不设 width/height 属性，不在 style 里同时锁死 w 和 h。
      // 只锁 height + max-width，让 CSS 按图片原生宽高比渲染，避免任何拉伸变形。
      height={h}
      className={`block flex-shrink-0 select-none ${className}`}
      style={{ height: `${h}px`, width: 'auto', maxWidth: 'none' }}
      draggable={false}
    />
  );
}

