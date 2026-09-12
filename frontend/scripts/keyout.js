// Flood-fill 从四个边缘把"接近背景色"的连通区域变透明
// 保护中间的 logo 笔画（哪怕是黑/白色，只要不连到边缘就保留）
//
// 阈值策略：
//   - 4 个角采样得到背景色（黑或白）
//   - 对每个像素：如果"到背景色的色差 < threshold"，就算背景候选
//   - BFS/DFS 从四个边缘出发，只把"从边缘可达"的背景候选变透明

const sharp = require('sharp');
const fs = require('fs');

const THRESHOLD = 80; // 色差阈值（更宽容，照顾抗锯齿边缘）
const TOP_N = 5; // 取出现最多的 5 种颜色作为背景候选

function colorDist(r, g, b, br, bg, bb) {
  return Math.sqrt((r-br)**2 + (g-bg)**2 + (b-bb)**2);
}

async function processLogo(src, out) {
  const img = sharp(src);
  const meta = await img.metadata();
  const { width: w, height: h, channels: ch } = meta;
  const raw = await img.raw().toBuffer();

  // 直方图：统计出现最多的颜色（粗分桶到 16）
  const bucket = new Map();
  for (let p = 0; p < w*h; p++) {
    const i = p * ch;
    const key = `${Math.round(raw[i]/16)*16},${Math.round(raw[i+1]/16)*16},${Math.round(raw[i+2]/16)*16}`;
    bucket.set(key, (bucket.get(key)||0)+1);
  }
  const sorted = [...bucket.entries()].sort((a,b)=>b[1]-a[1]).slice(0, TOP_N);
  console.log(`\n${src.split('/').pop()} top colors:`);
  sorted.forEach(([k,v]) => console.log(`  rgb≈${k} count=${v}`));

  // 取出现最多的颜色作为背景色
  const [bgKey] = sorted[0];
  const [br, bg, bb] = bgKey.split(',').map(Number);
  console.log(`  -> bg = rgb(${br},${bg},${bb})`);

  // 计算"背景候选"mask
  const W = w, H = h;
  const candidate = new Uint8Array(W * H);
  for (let p = 0; p < W*H; p++) {
    const i = p * ch;
    const d = colorDist(raw[i], raw[i+1], raw[i+2], br, bg, bb);
    candidate[p] = d < THRESHOLD ? 1 : 0;
  }

  // BFS 从四个边缘扩散
  const reachable = new Uint8Array(W * H);
  const queue = [];
  for (let x = 0; x < W; x++) {
    queue.push(x); queue.push((H-1)*W + x);
    reachable[x] = 1; reachable[(H-1)*W + x] = 1;
  }
  for (let y = 0; y < H; y++) {
    queue.push(y*W); queue.push(y*W + (W-1));
    reachable[y*W] = 1; reachable[y*W + (W-1)] = 1;
  }
  let head = 0;
  while (head < queue.length) {
    const p = queue[head++];
    const x = p % W, y = (p / W) | 0;
    for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
      const nx = x+dx, ny = y+dy;
      if (nx<0 || nx>=W || ny<0 || ny>=H) continue;
      const np = ny*W + nx;
      if (reachable[np]) continue;
      if (!candidate[np]) continue;
      reachable[np] = 1;
      queue.push(np);
    }
  }

  const out4 = Buffer.alloc(W * H * 4);
  let removed = 0, kept = 0;
  for (let p = 0; p < W*H; p++) {
    const i = p * ch, o = p * 4;
    if (reachable[p] && candidate[p]) {
      out4[o] = 0; out4[o+1] = 0; out4[o+2] = 0; out4[o+3] = 0;
      removed++;
    } else {
      out4[o] = raw[i]; out4[o+1] = raw[i+1]; out4[o+2] = raw[i+2]; out4[o+3] = 255;
      kept++;
    }
  }
  console.log(`  removed: ${removed}px (${(removed/(W*H)*100).toFixed(1)}%), kept: ${kept}px`);

  await sharp(out4, { raw: { width: W, height: H, channels: 4 } })
    .png({ compressionLevel: 9 })
    .toFile(out);
  console.log(`  wrote: ${out}`);
}

(async () => {
  await processLogo(
    'public/brand/gac-logo-light.png',
    'public/brand/gac-logo-light.png.tmp',
  );
  await processLogo(
    'public/brand/gac-logo-dark.png',
    'public/brand/gac-logo-dark.png.tmp',
  );
  fs.renameSync('public/brand/gac-logo-light.png.tmp', 'public/brand/gac-logo-light.png');
  fs.renameSync('public/brand/gac-logo-dark.png.tmp', 'public/brand/gac-logo-dark.png');
  console.log('\ndone.');
})();
