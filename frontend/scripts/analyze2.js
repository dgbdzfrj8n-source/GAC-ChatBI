// 统计整张图的非黑像素数 + 颜色直方图
const sharp = require('sharp');

async function analyze(src) {
  const img = sharp(src);
  const meta = await img.metadata();
  const { width: w, height: h, channels: ch } = meta;
  const raw = await img.raw().toBuffer();

  let blackCount = 0, whiteCount = 0, otherCount = 0;
  let rHist = new Map(); // 颜色出现次数直方图（粗分桶）
  const sample = [];

  for (let p = 0; p < w * h; p++) {
    const i = p * ch;
    const r = raw[i], g = raw[i+1], b = raw[i+2];
    if (r < 5 && g < 5 && b < 5) blackCount++;
    else if (r > 250 && g > 250 && b > 250) whiteCount++;
    else {
      otherCount++;
      if (sample.length < 8) sample.push({ p, r, g, b, x: p % w, y: (p / w) | 0 });
    }
    if (otherCount < 100000) {
      const key = `${Math.round(r/16)*16},${Math.round(g/16)*16},${Math.round(b/16)*16}`;
      rHist.set(key, (rHist.get(key)||0)+1);
    }
  }

  console.log(`\n=== ${src.split('/').pop()} ===`);
  console.log(`total: ${w*h}, black: ${blackCount}, white: ${whiteCount}, other: ${otherCount}`);
  console.log(`first 8 non-black samples:`, sample);
  const top = [...rHist.entries()].sort((a,b)=>b[1]-a[1]).slice(0, 8);
  console.log('top 8 color buckets (RGB粗分, count):', top);
}

(async () => {
  await analyze('public/brand/gac-logo-light.png');
  await analyze('public/brand/gac-logo-dark.png');
})();
