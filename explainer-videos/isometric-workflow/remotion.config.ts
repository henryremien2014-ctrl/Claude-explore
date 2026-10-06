import fs from 'node:fs';
import {Config} from '@remotion/cli/config';

// Lossless frames keep flat colours and text edges clean before H.264 encoding.
Config.setVideoImageFormat('png');
Config.setCodec('h264');
Config.setCrf(16);
Config.setPixelFormat('yuv420p');
Config.setOverwriteOutput(true);

// Prefer a Chromium already on the machine (set REMOTION_BROWSER to choose one);
// if none is found, Remotion downloads its own.
const browser =
	process.env.REMOTION_BROWSER ??
	'/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
if (browser && fs.existsSync(browser)) {
	Config.setBrowserExecutable(browser);
}
