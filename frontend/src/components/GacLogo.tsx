'use client';

// 广汽集团标志组件（SVG 精准还原版）
// 设计参考：广汽集团官方 LOGO
// 结构：外层红色椭圆细边框 + 内层蓝色实心椭圆 + 白色粗体 G 字

interface GacLogoProps {
  size?: 'sm' | 'md' | 'lg' | number;
}

export default function GacLogo({ size = 'md' }: GacLogoProps) {
  const sizeMap = {
    sm: { outer: 32, fontSize: 13, redStroke: 1.2 },
    md: { outer: 40, fontSize: 17, redStroke: 1.5 },
    lg: { outer: 52, fontSize: 22, redStroke: 1.8 },
  };

  const s = typeof size === 'number'
    ? { outer: size, fontSize: size * 0.43, redStroke: size * 0.038 }
    : sizeMap[size];

  const center = s.outer / 2;
  // 椭圆更扁一些（高度约为宽度的 78%）
  const rx = center - s.redStroke; // 给红色边框留位置
  const ry = rx * 0.78;

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
        {/* 内层蓝色渐变（广汽蓝） */}
        <linearGradient id="gacBlueGrad2" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#003C8F" />
          <stop offset="50%" stopColor="#00449E" />
          <stop offset="100%" stopColor="#0050B8" />
        </linearGradient>
      </defs>

      {/* ① 外层蓝色实心椭圆（作为底色，被红色边框包裹） */}
      <ellipse
        cx={center}
        cy={center}
        rx={rx}
        ry={ry}
        fill="url(#gacBlueGrad2)"
      />

      {/* ② 红色椭圆细边框（圈在外圈） */}
      <ellipse
        cx={center}
        cy={center}
        rx={rx}
        ry={ry}
        fill="none"
        stroke="#C8102E"
        strokeWidth={s.redStroke}
      />

      {/* ③ G 字母（白色粗体，几乎占满蓝椭圆） */}
      <text
        x={center}
        y={center + s.fontSize * 0.36}
        textAnchor="middle"
        fill="white"
        fontSize={s.fontSize}
        fontWeight="900"
        fontFamily="-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif"
        letterSpacing="-1"
      >
        G
      </text>
    </svg>
  );
}
