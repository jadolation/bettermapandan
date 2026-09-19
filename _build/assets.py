import re
import shutil
import subprocess
import sys
from pathlib import Path

from _build.config import ROOT, FIL_DIR, PAG_DIR
from _build.templates import to_folder_index


def generate_sitemap() -> None:
    """Generate sitemap.xml with hreflang alternate links for EN/FIL."""
    import datetime
    from urllib.parse import quote

    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    base_url = "https://bettermapandan.org"

    def _is_output_index(path: Path) -> bool:
        """Check if an index.html is a build output, not a source/template file."""
        parts = path.parts
        if any(part in ("src", "node_modules", ".venv", ".git", "__pycache__", ".kilo") for part in parts):
            return False
        if path.name != "index.html":
            return False
        # Skip hidden directories (worktrees, tooling) and development artifacts
        if any(part.startswith(".") for part in parts):
            return False
        # Skip development artifacts
        if "index_new" in parts:
            return False
        return True

    en_files = sorted([f for f in ROOT.rglob("index.html") if _is_output_index(f)])
    fil_files = sorted([f for f in FIL_DIR.rglob("index.html") if _is_output_index(f)]) if FIL_DIR.exists() else []
    pag_files = sorted([f for f in PAG_DIR.rglob("index.html") if _is_output_index(f)]) if PAG_DIR.exists() else []

    en_paths = {f.relative_to(ROOT).as_posix() for f in en_files}
    fil_paths = {f.relative_to(FIL_DIR).as_posix() for f in fil_files}
    pag_paths = {f.relative_to(PAG_DIR).as_posix() for f in pag_files}
    all_paths = sorted(en_paths | fil_paths | pag_paths)

    def _get_priority(path_str: str) -> str:
        """Set priority based on page type."""
        if path_str == "index.html":
            return "1.0"
        # Section pages - check if it's a direct child like "about/index.html"
        section_pages = ["about", "government", "legislative", "statistics", "transparency", "search"]
        parts = Path(path_str).parts
        if len(parts) == 2 and parts[0] in section_pages and parts[1] == "index.html":
            return "0.8"
        # Support pages
        if "support" in parts:
            return "0.5"
        # Service detail pages
        if "services" in parts and len(parts) > 2:
            return "0.6"
        # Services directory
        if len(parts) == 2 and parts[0] == "services" and parts[1] == "index.html":
            return "0.8"
        return "0.7"

    seen_urls = set()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]

    for path in all_paths:
        rel = Path(path)
        folder_path = to_folder_index(rel)
        if str(folder_path) == "index.html":
            en_url = f"{base_url}/"
            fil_url = f"{base_url}/fil/"
            pag_url = f"{base_url}/pag/"
        else:
            folder_str = quote(str(folder_path.parent), safe="/")
            if folder_path.parts and folder_path.parts[0] == "fil":
                en_folder = "/".join(folder_path.parts[1:-1])
                en_url = f"{base_url}/{en_folder}/" if en_folder else f"{base_url}/"
                fil_url = f"{base_url}/{folder_str}/"
                pag_url = f"{base_url}/pag/{en_folder}/" if en_folder else f"{base_url}/pag/"
            elif folder_path.parts and folder_path.parts[0] == "pag":
                en_folder = "/".join(folder_path.parts[1:-1])
                en_url = f"{base_url}/{en_folder}/" if en_folder else f"{base_url}/"
                pag_url = f"{base_url}/{folder_str}/"
                fil_url = f"{base_url}/fil/{en_folder}/" if en_folder else f"{base_url}/fil/"
            else:
                en_url = f"{base_url}/{folder_str}/"
                fil_url = f"{base_url}/fil/{folder_str}/"
                pag_url = f"{base_url}/pag/{folder_str}/"
        # Deduplicate by en_url
        if en_url in seen_urls:
            continue
        seen_urls.add(en_url)
        priority = _get_priority(path)
        lines.extend([
            "  <url>",
            f"    <loc>{en_url}</loc>",
            f"    <lastmod>{today}</lastmod>",
            "    <changefreq>monthly</changefreq>",
            f"    <priority>{priority}</priority>",
            f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>',
            f'    <xhtml:link rel="alternate" hreflang="fil" href="{fil_url}"/>',
            f'    <xhtml:link rel="alternate" hreflang="pag" href="{pag_url}"/>',
            "  </url>",
        ])

    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  sitemap.xml: {len(seen_urls)} URLs")


def generate_llms_txt() -> None:
    """Copy llms.txt to output root for AI agent discovery."""
    llms_src = ROOT / "llms.txt"
    if llms_src.exists():
        llms_content = llms_src.read_text(encoding="utf-8")
        (ROOT / "llms.txt").write_text(llms_content, encoding="utf-8")
        print("  llms.txt: copied")
    else:
        print("  llms.txt: not found, skipping")


CSS_COMMENT_RE = re.compile(r"/\*[^*]*\*+(?:[^/*][^*]*\*+)*/")
CSS_WHITESPACE_RE = re.compile(r"\s+")
CSS_BRACE_RE = re.compile(r"\s*([{}:;,])\s*")
CSS_TRAILING_RE = re.compile(r";\s*}")
CSS_LEADING_RE = re.compile(r"^\s+", re.MULTILINE)


def minify_css(css_text: str) -> str:
    """Remove CSS comments and unnecessary whitespace."""
    css = CSS_COMMENT_RE.sub("", css_text)
    css = CSS_WHITESPACE_RE.sub(" ", css)
    css = CSS_BRACE_RE.sub(r"\1", css)
    css = CSS_TRAILING_RE.sub("}", css)
    return CSS_LEADING_RE.sub("", css).strip()


def resolve_css_imports(css_text: str, base_path: Path) -> str:
    """Resolve @import url(...) directives by inlining the referenced files.

    Processes imports sequentially so that ordering is preserved.
    Handles nested imports up to 5 levels deep to prevent infinite loops.
    """
    import_re = re.compile(r'@import\s+url\(["\']?([^"\')]+)["\']?\)\s*;')
    resolved = []
    seen = set()

    def _resolve(text: str, depth: int = 0) -> str:
        if depth > 5:
            return text

        def _replace(match):
            import_path = match.group(1)
            abs_path = (base_path / import_path).resolve()

            if abs_path in seen:
                return ""
            seen.add(abs_path)

            if not abs_path.exists():
                print(f"  WARNING: CSS import not found: {import_path}")
                return ""

            partial = abs_path.read_text(encoding="utf-8")
            return _resolve(partial, depth + 1)

        return import_re.sub(_replace, text)

    return _resolve(css_text)


def minify_assets() -> None:
    """Minify CSS and JS assets.

    Resolves @import directives in style.css manifest, inlining all partials
    into a single minified style.min.css for production. Minifies first-party
    JS to .min.js sidecars (vendored chart.umd.min.js is already minified).
    """
    css_path = ROOT / "assets" / "style.css"
    css_min_path = ROOT / "assets" / "style.min.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")

        # Resolve @import directives if manifest uses them
        if "@import" in css:
            css = resolve_css_imports(css, css_path.parent)

        css_min = minify_css(css)
        css_min_path.write_text(css_min, encoding="utf-8")
        orig_size = len(css.encode("utf-8"))
        min_size = len(css_min.encode("utf-8"))
        pct = ((1 - min_size / orig_size) * 100) if orig_size > 0 else 0
        print(f"  style.css: {orig_size:,} → {min_size:,} bytes ({pct:.1f}% reduction)")

    minify_js_assets()


# First-party scripts minified to .min.js sidecars. Vendored
# chart.umd.min.js ships minified already and is intentionally excluded.
JS_SOURCES = [
    "assets/script.js",
    "assets/barangay-data.js",
    "assets/services.js",
    "assets/service-filter.js",
    "assets/legislative.js",
    "assets/stats.js",
    "assets/transparency.js",
    "assets/search.js",
    "assets/report.js",
    "assets/leaflet-map.js",
    "assets/font-loader.js",
    "assets/chart-loader.js",
    "assets/js/common.js",
    "assets/js/procurement-table.js",
    "assets/js/dpwh-table.js",
    "assets/js/transparency-charts.js",
    "assets/js/fdp-dashboard.js",
    "assets/js/coa-projects-table.js",
    "assets/js/dashboard-tabs.js",
]


def minify_js_assets() -> None:
    """Minify first-party JS via esbuild, falling back to copy-through.

    Always writes <name>.min.js next to each source so HTML references stay
    valid even when esbuild is unavailable (offline CI). Never modifies
    the original sources.
    """
    total_orig, total_new, count = 0, 0, 0
    for rel in JS_SOURCES:
        src = ROOT / rel
        if not src.exists():
            print(f"  WARNING: JS source not found: {rel}")
            continue
        dst = src.with_name(src.stem + ".min.js")
        try:
            proc = subprocess.run(
                ["npx", "--yes", "esbuild", str(src), "--minify",
                 f"--outfile={dst}"],
                capture_output=True, text=True, timeout=90, cwd=ROOT,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip()[:200])
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:  # offline/esbuild missing
            print(f"  WARNING: esbuild failed for {rel} ({exc}); copying unminified")
            dst.write_bytes(src.read_bytes())
        total_orig += src.stat().st_size
        total_new += dst.stat().st_size
        count += 1
    if count:
        pct = ((1 - total_new / total_orig) * 100) if total_orig else 0
        print(f"  JS: {total_orig:,} → {total_new:,} bytes across {count} files ({pct:.1f}% reduction)")


def compress_images() -> None:
    """Compress images and convert to WebP using sharp (Node.js).

    Operations:
    - JPGs in citizens-charter: compress with mozjpeg, quality 70, max-width 1200
    - PNGs in history/: compress with png compression, quality 60, max-width 1200
    - Hero images: convert to WebP (luyan.png, Pandan.jpg, plaza.jpg)
    - History PNGs: convert to WebP
    """
    compress_script = ROOT / "compress.mjs"
    script_content = r"""import sharp from "sharp";
import fs from "fs";
import path from "path";

const MAX_WIDTH = 1200;
const MAX_WIDTH_LOGO = 400;
const WEBP_QUALITY = 80;

async function compressJpg(dir) {
  const files = fs.readdirSync(dir).filter(f => f.endsWith(".jpg"));
  let totalBefore = 0, totalAfter = 0, count = 0;
  for (const file of files) {
    const filePath = path.join(dir, file);
    const before = fs.statSync(filePath).size;
    totalBefore += before;
    try {
      const img = sharp(filePath);
      const meta = await img.metadata();
      let pipeline = img.jpeg({ quality: 70, mozjpeg: true });
      if (meta.width && meta.width > MAX_WIDTH) {
        pipeline = pipeline.resize(MAX_WIDTH, null, { withoutEnlargement: true });
      }
      const buf = await pipeline.toBuffer();
      fs.writeFileSync(filePath, buf);
      totalAfter += buf.length;
      count++;
    } catch (err) {
      console.error(`  SKIP ${file}: ${err.message}`);
    }
  }
  return { count, totalBefore, totalAfter };
}

async function compressPng(dir) {
  const files = fs.readdirSync(dir).filter(f => f.endsWith(".png"));
  let totalBefore = 0, totalAfter = 0, count = 0;
  for (const file of files) {
    const filePath = path.join(dir, file);
    const before = fs.statSync(filePath).size;
    totalBefore += before;
    try {
      const img = sharp(filePath);
      const meta = await img.metadata();
      let pipeline = img.png({ quality: 60, compressionLevel: 9 });
      if (meta.width && meta.width > MAX_WIDTH) {
        pipeline = pipeline.resize(MAX_WIDTH, null, { withoutEnlargement: true });
      }
      const buf = await pipeline.toBuffer();
      fs.writeFileSync(filePath, buf);
      totalAfter += buf.length;
      count++;
    } catch (err) {
      console.error(`  SKIP ${file}: ${err.message}`);
    }
  }
  return { count, totalBefore, totalAfter };
}

async function convertToWebP(inputPath, outputPath, maxWidth) {
  try {
    const before = fs.statSync(inputPath).size;
    const img = sharp(inputPath);
    const meta = await img.metadata();
    let pipeline = img.webp({ quality: WEBP_QUALITY });
    if (meta.width && meta.width > maxWidth) {
      pipeline = pipeline.resize(maxWidth, null, { withoutEnlargement: true });
    }
    const buf = await pipeline.toBuffer();
    fs.writeFileSync(outputPath, buf);
    const after = buf.length;
    const savings = ((1 - after / before) * 100).toFixed(1);
    console.log(`  ${path.basename(inputPath)}: ${(before / 1024).toFixed(1)} KB -> ${(after / 1024).toFixed(1)} KB (${savings}% reduction)`);
    return { before, after, count: 1 };
  } catch (err) {
    console.error(`  ERROR converting ${inputPath}: ${err.message}`);
    return { before: 0, after: 0, count: 0 };
  }
}

async function extractPngFromSvg(svgPath, outputPath) {
  try {
    const svgContent = fs.readFileSync(svgPath, 'utf8');
    const base64Match = svgContent.match(/xlink:href="data:image\/png;base64,([^"]+)"/);
    if (!base64Match) {
      console.error(`  Could not find embedded PNG in ${svgPath}`);
      return { before: 0, after: 0, count: 0 };
    }
    const base64Data = base64Match[1];
    const pngBuffer = Buffer.from(base64Data, 'base64');
    fs.writeFileSync(outputPath, pngBuffer);
    console.log(`  Extracted PNG from SVG: ${path.basename(outputPath)} (${(pngBuffer.length / 1024).toFixed(1)} KB)`);
    return { before: pngBuffer.length, after: pngBuffer.length, count: 1 };
  } catch (err) {
    console.error(`  ERROR extracting from SVG ${svgPath}: ${err.message}`);
    return { before: 0, after: 0, count: 0 };
  }
}

async function main() {
  console.log("=== Optimizing images for performance ===\n");

  console.log("1. Citizen's Charter JPGs (compression)...");
  const jpg = await compressJpg("assets/citizens-charter");
  const jpgPct = ((1 - jpg.totalAfter / jpg.totalBefore) * 100).toFixed(1);
  console.log(`  JPGs: ${jpg.count} files, ${(jpg.totalBefore/1e6).toFixed(2)}MB -> ${(jpg.totalAfter/1e6).toFixed(2)}MB (${jpgPct}%)`);

  console.log("\n2. History PNGs (compression)...");
  const png = await compressPng("assets/history");
  const pngPct = ((1 - png.totalAfter / png.totalBefore) * 100).toFixed(1);
  console.log(`  PNGs: ${png.count} files, ${(png.totalBefore/1e6).toFixed(2)}MB -> ${(png.totalAfter/1e6).toFixed(2)}MB (${pngPct}%)`);

  console.log("\n3. Converting hero images to WebP...");
  const heroImages = [
    ["assets/luyan.png", "assets/luyan.webp", MAX_WIDTH],
    ["assets/Pandan.jpg", "assets/Pandan.webp", MAX_WIDTH],
    ["assets/plaza.jpg", "assets/plaza.webp", MAX_WIDTH],
  ];
  let heroTotalBefore = 0, heroTotalAfter = 0, heroCount = 0;
  for (const [input, output, maxW] of heroImages) {
    if (fs.existsSync(input)) {
      const result = await convertToWebP(input, output, maxW);
      heroTotalBefore += result.before;
      heroTotalAfter += result.after;
      heroCount += result.count;
    }
  }
  console.log(`  Hero images: ${heroCount} files, ${(heroTotalBefore/1e6).toFixed(2)}MB -> ${(heroTotalAfter/1e6).toFixed(2)}MB`);

  console.log("\n4. Converting history images to WebP...");
  const historyDir = "assets/history";
  let histWebpBefore = 0, histWebpAfter = 0, histCount = 0;
  if (fs.existsSync(historyDir)) {
    const histFiles = fs.readdirSync(historyDir).filter(f => f.endsWith(".png"));
    for (const file of histFiles) {
      const inputPath = path.join(historyDir, file);
      const outputPath = path.join(historyDir, file.replace('.png', '.webp'));
      const result = await convertToWebP(inputPath, outputPath, MAX_WIDTH);
      histWebpBefore += result.before;
      histWebpAfter += result.after;
      histCount += result.count;
    }
    console.log(`  History WebP: ${histCount} files, ${(histWebpBefore/1e6).toFixed(2)}MB -> ${(histWebpAfter/1e6).toFixed(2)}MB`);
  }

  const totalBefore = jpg.totalBefore + png.totalBefore + heroTotalBefore + histWebpBefore;
  const totalAfter = jpg.totalAfter + png.totalAfter + heroTotalAfter + histWebpAfter;
  console.log(`\n=== Total: ${(totalBefore/1e6).toFixed(2)}MB -> ${(totalAfter/1e6).toFixed(2)}MB (${((1-totalAfter/totalBefore)*100).toFixed(1)}% reduction) ===`);
}

main().catch(console.error);
"""
    compress_script.write_text(script_content, encoding="utf-8")
    import subprocess

    result = subprocess.run(
        ["node", str(compress_script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    compress_script.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"  Image compression failed: {result.stderr}", file=sys.stderr)
    else:
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
