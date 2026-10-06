import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';
import {FONTS} from './theme';

// loadFont holds the render until each font is in; this promise lets components
// wait too (labels are measured once the real font is available).
export const fontsReady = Promise.all(
	Object.values(FONTS).map((f) =>
		loadFont({family: f.family, url: staticFile(f.file), weight: f.weight}),
	),
);
