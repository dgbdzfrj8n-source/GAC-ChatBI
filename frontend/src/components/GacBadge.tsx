'use client';

// 广汽集团品牌徽标
// 用于 TopBar 右上角用户头像、二级页面顶部主图标等场景。
// 视觉：蓝色（广汽品牌色）圆角矩形背景 + 白色粗体字母。
// 默认读 pageTitleMap[当前路径].letter（数据驱动），未匹配时用 'G'。
// 也可通过 letter prop 显式覆盖（用于 AI 分析师等非页面场景）。

import { clsx } from 'clsx';
import { usePathname } from 'next/navigation';
import { pageTitleMap } from '@/lib/menu';

interface GacBadgeProps {
  size?: 'sm' | 'md' | 'lg' | number;
  letter?: string; // 拼音首字母（显式覆盖）；不传则自动从 pageTitleMap 取
  className?: string;
}

const SIZE_MAP: Record<Exclude<NonNullable<GacBadgeProps['size']>, number>, number> = {
  sm: 28,
  md: 36,
  lg: 56,
};

function resolveSize(size: GacBadgeProps['size']) {
  if (typeof size === 'number') return size;
  return SIZE_MAP[size ?? 'md'];
}

export default function GacBadge({ size = 'md', letter, className }: GacBadgeProps) {
  const px = resolveSize(size);
  const fontSize = Math.round(px * 0.55); // 字母占方块的 55%

  // 自动取当前页面的 letter
  const pathname = usePathname();
  const displayLetter = letter ?? pageTitleMap[pathname]?.letter ?? 'G';

  return (
    <div
      className={clsx(
        'inline-flex items-center justify-center rounded-lg flex-shrink-0 select-none',
        'bg-gradient-to-br from-blue-500 to-blue-700 text-white font-bold',
        'shadow-sm',
        className,
      )}
      style={{ width: `${px}px`, height: `${px}px`, fontSize: `${fontSize}px`, lineHeight: 1 }}
      aria-label={`徽标 ${displayLetter}`}
    >
      {displayLetter}
    </div>
  );
}
