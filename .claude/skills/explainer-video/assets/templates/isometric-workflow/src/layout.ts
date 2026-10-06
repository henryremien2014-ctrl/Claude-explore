import {COS30, makeProjector} from './iso';
import {FOOTER, STEPS, TITLE} from './steps';
import {LABEL_SIZE} from './theme';
import {WIDTH} from './timeline';

// Where everything sits. Sizes adapt to the number of steps; if the text can't
// fit, rendering stops with an error that says what to change.
export const N = STEPS.length;
if (N < 2 || N > 6) {
	throw new Error(`Use 2 to 6 steps (got ${N}). Split a longer process into two videos.`);
}

// Isometric units.
export const SPACING = 3; // distance between neighbouring blocks
export const HALF = 0.5; // half a block's footprint
export const BLOCK_H = 0.52; // block height once it has risen
export const ICON_SIZE = 0.76; // side of the square each icon is drawn into
export const TRACK_W = 0.1; // width of the trail the dot leaves
// Pixels per isometric unit: 152 for up to 4 steps, smaller beyond that so the
// row of blocks never spans more than 1400 px.
export const UNIT = Math.min(152, 1400 / ((N - 1) * SPACING * COS30));

// Labels, in pixels. They shrink a little for 5-6 steps so neighbours fit side
// by side; 60 px is still about 12 pt on a phone held upright.
export const LABEL_PX = Math.min(LABEL_SIZE, N >= 6 ? 60 : N === 5 ? 64 : LABEL_SIZE);
export const LABEL_LEADING = 1.06;
export const LABEL_LINE = LABEL_PX * LABEL_LEADING;
export const LABEL_GAP = 28; // between a block and its label
export const BADGE = LABEL_PX; // step-number circle
export const BADGE_GAP = Math.round(LABEL_PX * 0.32);
export const MARGIN = 60; // labels stay this far inside the frame edges
const SAME_ROW_GAP = 24; // minimum space between two labels in one row

// Zig-zag along the isometric axes: odd steps low, even steps high.
export const POSITIONS = STEPS.map((_, i) => ({
	x: Math.floor(i / 2) * SPACING,
	y: -Math.ceil(i / 2) * SPACING,
}));
export const isUpper = (i: number) => i % 2 === 1;

const linesIn = (upper: boolean) =>
	Math.max(1, ...STEPS.filter((_, i) => isUpper(i) === upper).map((s) => s.lines.length));
const upperLines = linesIn(true);
const lowerLines = linesIn(false);

// Vertical: centre the diagram (labels included) between the title and footer.
const BAND_TOP = TITLE ? 172 : 90;
const BAND_BOTTOM = FOOTER ? 904 : 1010;
const diagramHeight =
	upperLines * LABEL_LINE +
	LABEL_GAP +
	(HALF + BLOCK_H) * UNIT +
	0.5 * SPACING * UNIT +
	HALF * UNIT +
	LABEL_GAP +
	lowerLines * LABEL_LINE;
if (diagramHeight > BAND_BOTTOM - BAND_TOP + 1) {
	throw new Error(
		'The labels do not fit vertically. Keep upper-row labels (steps 2, 4, 6) to one line, ' +
			'or remove the title or footer.',
	);
}
const UPPER_LABEL_TOP = BAND_TOP + Math.max(0, (BAND_BOTTOM - BAND_TOP - diagramHeight) / 2);
const LOWER_ROW_Y =
	UPPER_LABEL_TOP + upperLines * LABEL_LINE + LABEL_GAP + (HALF + BLOCK_H) * UNIT + 0.5 * SPACING * UNIT;

// Horizontal: centre the blocks, nudged right when there is a title.
const diag = POSITIONS.map((p) => p.x - p.y);
const SHIFT_X = TITLE ? 40 : 0;
const ORIGIN_X =
	WIDTH / 2 + SHIFT_X - ((Math.min(...diag) + Math.max(...diag)) / 2) * COS30 * UNIT;

export const iso = makeProjector(ORIGIN_X, LOWER_ROW_Y, UNIT);

// Where each label's box starts (left edge) and its top/bottom anchor.
export const labelAnchorY = (i: number) => {
	const {x, y} = POSITIONS[i];
	const floor = iso(x, y, 0);
	return isUpper(i)
		? floor.Y - (HALF + BLOCK_H) * UNIT - LABEL_GAP // label's bottom edge
		: floor.Y + HALF * UNIT + LABEL_GAP; // label's top edge
};

// Centre each label under/over its block, pulled inside the frame margins,
// and refuse to render if two labels in the same row would touch.
export const placeLabels = (widths: number[]) => {
	const lefts = widths.map((w, i) => {
		const center = iso(POSITIONS[i].x, POSITIONS[i].y).X;
		return Math.min(Math.max(center - w / 2, MARGIN), WIDTH - MARGIN - w);
	});
	for (let i = 0; i + 2 < N; i++) {
		if (lefts[i] + widths[i] + SAME_ROW_GAP > lefts[i + 2]) {
			throw new Error(
				`Labels ${i + 1} and ${i + 3} overlap. Shorten them, split a lower-row label ` +
					'(steps 1, 3, 5) over two lines, or use fewer steps.',
			);
		}
	}
	return lefts;
};
