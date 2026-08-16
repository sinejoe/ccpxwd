// Deploy build step: minifies the served HTML/CSS/inline-JS and copies
// everything else (puzzle data, CNAME) through untouched. Source files stay
// fully commented in git -- only dist/, which GitHub Actions publishes to
// Pages, is stripped. Run via `npm run build`.
const fs = require('fs');
const path = require('path');
const { minify } = require('html-minifier-terser');

const ROOT = __dirname;
const DIST = path.join(ROOT, 'dist');

const HTML_FILES = ['index.html', 'archive.html', '404.html'];
const COPY_PATHS = ['puzzles', 'CNAME', '_redirects'];

const MINIFY_OPTS = {
  collapseWhitespace: true,
  removeComments: true,
  removeRedundantAttributes: true,
  removeScriptTypeAttributes: true,
  removeStyleLinkTypeAttributes: true,
  useShortDoctype: true,
  minifyCSS: true,
  minifyJS: { mangle: true, compress: true },
  collapseBooleanAttributes: true,
};

async function main(){
  fs.rmSync(DIST, { recursive: true, force: true });
  fs.mkdirSync(DIST, { recursive: true });

  for(const file of HTML_FILES){
    const src = fs.readFileSync(path.join(ROOT, file), 'utf8');
    const out = await minify(src, MINIFY_OPTS);
    fs.writeFileSync(path.join(DIST, file), out);
    console.log(`minified ${file}: ${src.length} -> ${out.length} bytes`);
  }

  for(const p of COPY_PATHS){
    fs.cpSync(path.join(ROOT, p), path.join(DIST, p), { recursive: true });
  }

  console.log('build complete ->', DIST);
}

main().catch(err => { console.error(err); process.exit(1); });
