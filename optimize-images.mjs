import sharp from "sharp";
import fs from "fs";
import path from "path";

const MAX_WIDTH_LOGO = 400;
const MAX_WIDTH_HERO = 1200;
const WEBP_QUALITY = 80;

async function extractPngFromSvg(svgPath, outputPath) {
    const svgContent = fs.readFileSync(svgPath, 'utf8');
    const base64Match = svgContent.match(/xlink:href="data:image\/png;base64,([^"]+)"/);
    if (!base64Match) {
        console.error(`  Could not find embedded PNG in ${svgPath}`);
        return false;
    }
    const base64Data = base64Match[1];
    const pngBuffer = Buffer.from(base64Data, 'base64');
    fs.writeFileSync(outputPath, pngBuffer);
    console.log(`  Extracted PNG from SVG: ${path.basename(outputPath)} (${(pngBuffer.length / 1024).toFixed(1)} KB)`);
    return true;
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
        console.log(`  ${path.basename(inputPath)}: ${(before / 1024).toFixed(1)} KB → ${(after / 1024).toFixed(1)} KB (${savings}% reduction)`);
        return true;
    } catch (err) {
        console.error(`  ERROR converting ${inputPath}: ${err.message}`);
        return false;
    }
}

async function main() {
    console.log("=== Optimizing images for Lighthouse performance ===\n");

    const assetsDir = "assets";

    console.log("1. Extracting and converting logo SVG to WebP...");
    const tempPng = path.join(assetsDir, "municipal-seal-temp.png");
    if (fs.existsSync(path.join(assetsDir, "logo-no-white.svg"))) {
        await extractPngFromSvg(path.join(assetsDir, "logo-no-white.svg"), tempPng);
        await convertToWebP(tempPng, path.join(assetsDir, "municipal-seal.svg"), MAX_WIDTH_LOGO);
        fs.unlinkSync(tempPng);
    }

    console.log("\n2. Converting hero background image (luyan.png)...");
    if (fs.existsSync(path.join(assetsDir, "luyan.png"))) {
        await convertToWebP(path.join(assetsDir, "luyan.png"), path.join(assetsDir, "luyan.webp"), MAX_WIDTH_HERO);
    }

    console.log("\n3. Converting hero images (Pandan.jpg, plaza.jpg)...");
    if (fs.existsSync(path.join(assetsDir, "Pandan.jpg"))) {
        await convertToWebP(path.join(assetsDir, "Pandan.jpg"), path.join(assetsDir, "Pandan.webp"), MAX_WIDTH_HERO);
    }
    if (fs.existsSync(path.join(assetsDir, "plaza.jpg"))) {
        await convertToWebP(path.join(assetsDir, "plaza.jpg"), path.join(assetsDir, "plaza.webp"), MAX_WIDTH_HERO);
    }

    console.log("\n4. Converting history PNGs to WebP...");
    const historyDir = path.join(assetsDir, "history");
    if (fs.existsSync(historyDir)) {
        const historyFiles = fs.readdirSync(historyDir).filter(f => f.endsWith(".png"));
        for (const file of historyFiles) {
            await convertToWebP(path.join(historyDir, file), path.join(historyDir, file.replace('.png', '.webp')), MAX_WIDTH_HERO);
        }
    }

    console.log("\n=== Optimization complete ===");
}

main().catch(console.error);
