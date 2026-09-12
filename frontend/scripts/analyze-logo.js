// 分析图：统计 4 个角 + 中点像素的白度/黑度
const sharp = require('sharp');

async function analyze(src) {
  const img = sharp(src);
  const meta = await img.metadata();
  const w = meta.width, h = meta.height;
  console.log(`\n=== ${src.split('/').pop()} ===`);
  console.log(`size: ${w}x${h}, channels: ${meta.channels}, hasAlpha: ${meta.hasAlpha}`);

  const raw = await img.raw().toBuffer();
  const ch = meta.channels;
  const samples = [
    [0, 0], [w-1, 0], [0, h-1], [w-1, h-1],          // 4 角
    [w>>1, h>>1],                                       // 中心
    [w>>2, h>>2], [(3*w)>>2, (3*h)>>2],               // 两个四分之一
  ];
  for (const [x, y] of samples) {
    const i = (y * w + x) * ch;
    const r = raw[i], g = raw[i+1], b = raw[i+2];
    const lum = Math.round(0.299*r + 0.587*g + 0.114*b);
    console.log(`  (${x},${y}) rgb=(${r},${g},${b})  lum=${lum}  ${lum>240?'白':lum<15?'黑':'灰'}`);
  }
}

(async () => {
  await analyze('public/brand/gac-logo-light.png');
  await analyze('public/brand/gac-logo-dark.png');
})();
