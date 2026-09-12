'use client';

// 广汽集团标志组件（SVG 还原版）
// 设计参考：广汽集团官方 LOGO - 椭圆 + G 字 + 红蓝配色

interface GacLogoProps {
  size?: 'sm' | 'md' | 'lg';
}

export default function GacLogo({ size = 'md' }: GacLogoProps) {
  const sizeMap = {
    sm: { outer: 28, inner: 22, fontSize: 10, border: 1.5 },
    md: { outer: 36, inner: 28, fontSize: 13, border: 2 },
    lg: { outer: 48, inner: 38, fontSize: 18, border: 2.5 },
  };
  const s = sizeMap[size];
  const center = s.outer / 2;

  return (
    <svg
      width={s.outer}
      height={s.outer}
      viewBox={`0 0 ${s.outer} ${s.outer}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* 外椭圆 - 广汽蓝渐变 */}
      <defs>
        <linearGradient id="gacBlue" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#003C8F" />
          <stop offset="100%" stopColor="#0050B8" />
        </linearGradient>
        <linearGradient id="gacRed" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#C8102E" />
          <stop offset="100%" stopColor="#E0112F" />
        </linearGradient>
      </defs>

      {/* 底色椭圆 */}
      <ellipse
        cx={center}
        cy={center}
        rx={center - s.border / 2}
        ry={center - s.border / 2}
        fill="url(#gacBlue)"
      />

      {/* 红色边框（广汽红） */}
      <ellipse
        cx={center}
        cy={center}
        rx={center - s.border / 2}
        ry={center - s.border / 2}
        fill="none"
        stroke="#C8102E"
        strokeWidth={s.border}
      />

      {/* 内椭圆装饰 */}
      <ellipse
        cx={center}
        cy={center}
        rx={center - s.border * 2.5}
        ry={center - s.border * 2.5}
        fill="none"
        stroke="rgba(255,255,255,0.2)"
        strokeWidth={0.5}
      />

      {/* G 字母（白色加粗体） */}
      <text
        x={center}
        y={center + s.fontSize * 0.35}
        textAnchor="middle"
        fill="white"
        fontSize={s.fontSize}
        fontWeight="800"
        fontFamily="-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif"
        letterSpacing="-1"
      >
        G
      </text>
    </svg>
  );
}
