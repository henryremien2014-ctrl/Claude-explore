// Render several stills from one bundle (much faster than repeated `remotion still`):
//   node scripts/stills.mjs 80 206 332 458 599
// Options via env: COMPOSITION=HowItWorks OUT_DIR=out/stills PREFIX=f
import fs from 'node:fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const frames = process.argv.slice(2).map(Number);
if (frames.length === 0 || frames.some((f) => !Number.isInteger(f))) {
	console.error('Usage: node scripts/stills.mjs <frame> [frame ...]');
	process.exit(1);
}
const id = process.env.COMPOSITION ?? 'HowItWorks';
const outDir = process.env.OUT_DIR ?? 'out/stills';
const prefix = process.env.PREFIX ?? 'f';
const preferred =
	process.env.REMOTION_BROWSER ??
	'/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
const browserExecutable = preferred && fs.existsSync(preferred) ? preferred : null;

const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const browser = await openBrowser('chrome', {browserExecutable});
const composition = await selectComposition({serveUrl, id, puppeteerInstance: browser});
fs.mkdirSync(outDir, {recursive: true});
for (const frame of frames) {
	const output = path.join(outDir, `${prefix}${String(frame).padStart(3, '0')}.png`);
	await renderStill({composition, serveUrl, frame, output, puppeteerInstance: browser});
	console.log('wrote', output);
}
await browser.close({silent: true});
