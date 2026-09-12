'use client';

// 广汽集团品牌徽标（早期 SVG 风格）
// 用于 TopBar 右上角用户头像、二级页面顶部主图标等不需要展示完整 Logo 图片的场景。
// 视觉：蓝色（广汽品牌色）圆角矩形背景 + 白色粗体 G。

import { clsx } from 'clsx';

interface GacBadgeProps {
  size?: 'sm' | 'md' | 'lg' | number;
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

export default function GacBadge({ size = 'md', className }: GacBadgeProps) {
  const px = resolveSize(size);
  const fontSize = Math.round(px * 0.55); // 字母 G 占方块的 55%

  return (
    <div
      className={clsx(
        'inline-flex items-center justify-center rounded-lg flex-shrink-0 select-none',
        'bg-gradient-to-br from-blue-500 to-blue-700 text-white font-bold',
        'shadow-sm',
        className,
      )}
      style={{ width: `${px}px`, height: `${px}px`, fontSize: `${fontSize}px`, lineHeight: 1 }}
      aria-label="广汽云 ChatBI"
    >
      G
    </div>
  );
}
