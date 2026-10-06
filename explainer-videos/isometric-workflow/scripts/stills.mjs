// Render several stills from one bundle: node scripts/stills.mjs 90 216 342 ...
// Optional: OUT_DIR=out/stills PREFIX=f node scripts/stills.mjs ...
import fs from 'node:fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const frames = process.argv.slice(2).map(Number);
const outDir = process.env.OUT_DIR ?? 'out/stills';
const prefix = process.env.PREFIX ?? 'f';
const preferred =
	process.env.REMOTION_BROWSER ??
	'/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
const browserExecutable = preferred && fs.existsSync(preferred) ? preferred : null;

const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const browser = await openBrowser('chrome', {browserExecutable});
const composition = await selectComposition({serveUrl, id: 'HowItWorks', puppeteerInstance: browser});
for (const frame of frames) {
	const output = path.join(outDir, `${prefix}${String(frame).padStart(3, '0')}.png`);
	await renderStill({composition, serveUrl, frame, output, puppeteerInstance: browser});
	console.log('wrote', output);
}
await browser.close({silent: true});
