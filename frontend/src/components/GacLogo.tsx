'use client';

// 广汽集团标志组件（SVG 精准还原版）
// 设计参考：广汽集团官方 LOGO
// 结构：外层红色椭圆边框 + 内层蓝色实心椭圆 + 白色 G 字

interface GacLogoProps {
  size?: 'sm' | 'md' | 'lg' | number;
}

export default function GacLogo({ size = 'md' }: GacLogoProps) {
  // 支持数字类型 size（自定义像素）
  const sizeMap = {
    sm: { outer: 32, fontSize: 11, redBorder: 2.5, blueBorder: 1 },
    md: { outer: 40, fontSize: 14, redBorder: 3, blueBorder: 1.2 },
    lg: { outer: 52, fontSize: 18, redBorder: 3.5, blueBorder: 1.5 },
  };

  const s = typeof size === 'number'
    ? { outer: size, fontSize: size * 0.4, redBorder: size * 0.08, blueBorder: size * 0.03 }
    : sizeMap[size];

  const center = s.outer / 2;
  // 外红椭圆半径（占据大部分空间）
  const redRx = center - 0.5;
  const redRy = redRx * 0.78; // 椭圆更扁一些
  // 内蓝椭圆半径（比红椭圆小一圈，留出红色边框宽度）
  const blueRx = redRx - s.redBorder;
  const blueRy = blueRx * 0.78;

  return (
    <svg
      width={s.outer}
      height={s.outer}
      viewBox={`0 0 ${s.outer} ${s.outer}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      <defs>
        {/* 外层红色渐变（广汽红） */}
        <linearGradient id="gacRedGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#D4152E" />
          <stop offset="100%" stopColor="#A8081F" />
        </linearGradient>
        {/* 内层蓝色渐变（广汽蓝） */}
        <linearGradient id="gacBlueGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#003C8F" />
          <stop offset="50%" stopColor="#00449E" />
          <stop offset="100%" stopColor="#0050B8" />
        </linearGradient>
        {/* 高光效果 */}
        <radialGradient id="gacHighlight" cx="0.35" cy="0.3" r="0.5">
          <stop offset="0%" stopColor="rgba(255,255,255,0.25)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0)" />
        </radialGradient>
      </defs>

      {/* 外层红色椭圆（实心，作为红色边框层） */}
      <ellipse
        cx={center}
        cy={center}
        rx={redRx}
        ry={redRy}
        fill="url(#gacRedGrad)"
      />

      {/* 内层蓝色椭圆（实心蓝底） */}
      <ellipse
        cx={center}
        cy={center}
        rx={blueRx}
        ry={blueRy}
        fill="url(#gacBlueGrad)"
      />

      {/* 蓝色高光叠加 */}
      <ellipse
        cx={center}
        cy={center}
        rx={blueRx}
        ry={blueRy}
        fill="url(#gacHighlight)"
      />

      {/* G 字母（白色加粗） */}
      <text
        x={center}
        y={center + s.fontSize * 0.36}
        textAnchor="middle"
        fill="white"
        fontSize={s.fontSize}
        fontWeight="900"
        fontFamily="-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif"
        letterSpacing="-0.5"
        style={{ paintOrder: 'stroke', stroke: 'rgba(0,0,0,0.05)', strokeWidth: 0.3 }}
      >
        G
      </text>
    </svg>
  );
}
