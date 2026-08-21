// Renders one puzzle's empty grid pattern as a 1200x630 OG/Twitter preview
// PNG. Deliberately draws only the grid (no title text baked into the
// image) -- link-preview cards show og:title as separate text alongside the
// image, and SVG text rendering depends on fonts being present in whatever
// environment runs the build (Cloudflare Pages' build container has no
// guarantee of matching this site's Georgia/serif look), so keeping the
// image to plain rects/lines keeps it deterministic everywhere.
const sharp = require('sharp');

const PAPER = '#f6f1e6';
const INK = '#1c1a17';

function escapeAttr(s){
  return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;');
}

function buildSvg(pattern){
  const SIZE = pattern.length;
  const W = 1200, H = 630;
  const margin = 40;
  const gridDim = Math.min(W, H) - margin * 2;
  const cell = gridDim / SIZE;
  const gx = (W - gridDim) / 2;
  const gy = (H - gridDim) / 2;

  let cells = '';
  for(let r=0;r<SIZE;r++){
    for(let c=0;c<SIZE;c++){
      const black = pattern[r][c] === '#';
      const x = gx + c*cell, y = gy + r*cell;
      cells += `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${cell.toFixed(2)}" height="${cell.toFixed(2)}" fill="${black?INK:'#fffdf8'}" stroke="${INK}" stroke-width="1.5"/>`;
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect x="0" y="0" width="${W}" height="${H}" fill="${escapeAttr(PAPER)}"/>
  <rect x="${gx-3}" y="${gy-3}" width="${gridDim+6}" height="${gridDim+6}" fill="none" stroke="${INK}" stroke-width="3"/>
  ${cells}
</svg>`;
}

async function renderGridPng(pattern, outPath){
  const svg = buildSvg(pattern);
  await sharp(Buffer.from(svg)).png().toFile(outPath);
}

module.exports = { renderGridPng };
