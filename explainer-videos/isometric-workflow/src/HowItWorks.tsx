import React, {useMemo} from 'react';
import {
	AbsoluteFill,
	Easing,
	interpolate,
	spring,
	staticFile,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import {loadFont} from '@remotion/fonts';
import {Icon} from './Icons';
import {COS30, makeProjector, toPoints} from './iso';
import {FOOTER, STEPS, TITLE} from './steps';
import {
	DOT_LEAVES,
	FOOTER_IN,
	HEIGHT,
	ICON_IN,
	LABEL_IN,
	RISE_FRAMES,
	TITLE_IN,
	WIDTH,
	stepStart,
} from './timeline';

loadFont({family: 'DM Sans', url: staticFile('fonts/dm-sans-700.woff2'), weight: '700'});
loadFont({family: 'DM Sans', url: staticFile('fonts/dm-sans-800.woff2'), weight: '800'});
loadFont({family: 'Fraunces', url: staticFile('fonts/fraunces-600.woff2'), weight: '600'});

// Palette: warm paper, muted teal blocks, one terracotta accent.
const BG = '#F5EFE4';
const GRID = '#E2D7C5';
const INK = '#24201C';
const MUTED = '#5F564C';
const ACCENT = '#CF633D';
const CREAM = '#FBF7EF';
const PAD = '#BFAE93';
const TOP = '#4F968B';
const LEFT = '#3D7B72';
const RIGHT = '#2F635C';
const EDGE = '#72B2A7';

// Layout, in isometric units.
const UNIT = 152; // pixels per unit
const HALF = 0.5; // half a block's footprint
const BLOCK_H = 0.52; // block height once it has risen
const SPACING = 3; // distance between neighbouring blocks
const ICON_SIZE = 0.76; // side of the square each icon is drawn into on the top face
const TRACK_W = 0.1; // width of the path the dot leaves behind
const LABEL_GAP = 28; // px between a block and its label
const LABEL_SIZE = 68;
const LABEL_LEADING = 1.06;
const LABEL_LINE = LABEL_SIZE * LABEL_LEADING;
const UPPER_LABEL_TOP = 172; // keeps the top row of labels clear of the title
// Screen y of the lower row's floor centre, worked back from the top label.
const LOWER_ROW_Y =
	UPPER_LABEL_TOP + LABEL_LINE + LABEL_GAP + (HALF + BLOCK_H) * UNIT + 0.5 * SPACING * UNIT;
const SHIFT_X = 40; // nudge right, away from the title
const ARRIVE_EARLY = 4; // the dot lands this many frames before its block rises

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Zig-zag: 1 low, 2 high, 3 low, 4 high, moving along the isometric axes.
const POSITIONS = STEPS.map((_, i) => ({
	x: Math.floor(i / 2) * SPACING,
	y: -Math.ceil(i / 2) * SPACING,
}));

const diag = POSITIONS.map((p) => p.x - p.y);
const ORIGIN_X =
	WIDTH / 2 + SHIFT_X - ((Math.min(...diag) + Math.max(...diag)) / 2) * COS30 * UNIT;
const iso = makeProjector(ORIGIN_X, LOWER_ROW_Y, UNIT);

const isUpper = (i: number) => i % 2 === 1;

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// Points along the route, in iso units, from block 0 up to `progress`
// (progress = segment index + fraction along it).
const routeTo = (progress: number) => {
	const pts = [POSITIONS[0]];
	const whole = Math.floor(progress);
	for (let i = 1; i <= whole && i < POSITIONS.length; i++) {
		pts.push(POSITIONS[i]);
	}
	const frac = progress - whole;
	if (frac > 0 && whole + 1 < POSITIONS.length) {
		const a = POSITIONS[whole];
		const b = POSITIONS[whole + 1];
		pts.push({x: lerp(a.x, b.x, frac), y: lerp(a.y, b.y, frac)});
	}
	return pts;
};

// A flat band on the floor between two route points (segments are axis-aligned).
const trackSegment = (a: {x: number; y: number}, b: {x: number; y: number}) => {
	const w = TRACK_W / 2;
	const alongX = Math.abs(b.x - a.x) > Math.abs(b.y - a.y);
	const corners = alongX
		? [iso(a.x, a.y - w), iso(b.x, b.y - w), iso(b.x, b.y + w), iso(a.x, a.y + w)]
		: [iso(a.x - w, a.y), iso(b.x - w, b.y), iso(b.x + w, b.y), iso(a.x + w, a.y)];
	return toPoints(corners);
};

const footprint = (x: number, y: number, z = 0) => [
	iso(x - HALF, y - HALF, z),
	iso(x + HALF, y - HALF, z),
	iso(x + HALF, y + HALF, z),
	iso(x - HALF, y + HALF, z),
];

const Block: React.FC<{i: number; h: number; iconIn: number}> = ({i, h, iconIn}) => {
	const {x, y} = POSITIONS[i];
	const top = footprint(x, y, h);
	const right = [
		iso(x + HALF, y - HALF, 0),
		iso(x + HALF, y + HALF, 0),
		iso(x + HALF, y + HALF, h),
		iso(x + HALF, y - HALF, h),
	];
	const left = [
		iso(x - HALF, y + HALF, 0),
		iso(x + HALF, y + HALF, 0),
		iso(x + HALF, y + HALF, h),
		iso(x - HALF, y + HALF, h),
	];

	// Lay the 100x100 icon flat on the top face: icon "right" runs up-right
	// along -y, icon "down" runs down-right along +x.
	const c = iso(x, y, h);
	const k = (ICON_SIZE * UNIT) / 100;
	const a = k * COS30;
	const matrix = `matrix(${a} ${-k / 2} ${a} ${k / 2} ${c.X - a * 100} ${c.Y})`;
	const scale = interpolate(iconIn, [0, 1], [0.7, 1]);

	return (
		<g>
			<polygon points={toPoints(left)} fill={LEFT} />
			<polygon points={toPoints(right)} fill={RIGHT} />
			<polygon points={toPoints(top)} fill={TOP} stroke={EDGE} strokeWidth={2} strokeLinejoin="round" />
			{iconIn > 0 ? (
				<g transform={matrix} opacity={iconIn}>
					<g transform={`translate(50 50) scale(${scale}) translate(-50 -50)`}>
						<Icon name={STEPS[i].icon} color={CREAM} />
					</g>
				</g>
			) : null}
		</g>
	);
};

const Label: React.FC<{i: number; progress: number}> = ({i, progress}) => {
	const {x, y} = POSITIONS[i];
	const upper = isUpper(i);
	const floor = iso(x, y, 0);
	const anchorY = upper
		? floor.Y - (HALF + BLOCK_H) * UNIT - LABEL_GAP
		: floor.Y + HALF * UNIT + LABEL_GAP;
	const shift = interpolate(progress, [0, 1], [upper ? 14 : -14, 0]);

	return (
		<div
			style={{
				position: 'absolute',
				left: floor.X,
				top: anchorY,
				transform: `translate(-50%, ${upper ? '-100%' : '0%'}) translateY(${shift}px)`,
				opacity: progress,
				display: 'flex',
				alignItems: 'flex-start',
				gap: 22,
				whiteSpace: 'nowrap',
			}}
		>
			<div
				style={{
					width: 66,
					height: 66,
					marginTop: 5,
					borderRadius: 33,
					background: ACCENT,
					color: CREAM,
					fontFamily: 'DM Sans',
					fontWeight: 800,
					fontSize: 40,
					lineHeight: '66px',
					textAlign: 'center',
					flexShrink: 0,
				}}
			>
				{i + 1}
			</div>
			<div
				style={{
					fontFamily: 'DM Sans',
					fontWeight: 700,
					fontSize: LABEL_SIZE,
					lineHeight: LABEL_LEADING,
					letterSpacing: '-0.01em',
					color: INK,
				}}
			>
				{STEPS[i].lines.map((line) => (
					<div key={line}>{line}</div>
				))}
			</div>
		</div>
	);
};

export const HowItWorks: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	// Faint isometric dot grid: "graph paper" for the scene to sit on.
	const gridDots = useMemo(() => {
		const dots: {X: number; Y: number}[] = [];
		for (let gx = -16; gx <= 16; gx += 0.5) {
			for (let gy = -22; gy <= 12; gy += 0.5) {
				const p = iso(gx, gy, 0);
				if (p.X > -10 && p.X < WIDTH + 10 && p.Y > -10 && p.Y < HEIGHT + 10) {
					dots.push(p);
				}
			}
		}
		return dots;
	}, []);

	const ease = Easing.inOut(Easing.cubic);

	// How far the dot has travelled along the route (segment index + fraction).
	let progress = 0;
	let dotVisible = false;
	for (let i = 0; i < STEPS.length - 1; i++) {
		const leave = stepStart(i) + DOT_LEAVES;
		const arrive = stepStart(i + 1) - ARRIVE_EARLY;
		if (frame >= leave) {
			progress = i + interpolate(frame, [leave, arrive], [0, 1], {...clamp, easing: ease});
		}
		if (frame >= leave && frame <= stepStart(i + 1) + 2) {
			dotVisible = true;
		}
	}
	const route = routeTo(progress);
	const dotPos = route[route.length - 1];
	const dotScreen = iso(dotPos.x, dotPos.y, 0);

	const titleIn = interpolate(frame, TITLE_IN, [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
	const footerIn = interpolate(frame, FOOTER_IN, [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});

	// Back-to-front order so nearer blocks are painted over farther ones.
	const drawOrder = STEPS.map((_, i) => i).sort(
		(a, b) => POSITIONS[a].x + POSITIONS[a].y - (POSITIONS[b].x + POSITIONS[b].y),
	);

	return (
		<AbsoluteFill style={{backgroundColor: BG}}>
			<svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
				{gridDots.map((p, idx) => (
					<circle key={idx} cx={p.X} cy={p.Y} r={2.4} fill={GRID} />
				))}

				{/* Landing pads: where the next block will rise. */}
				{STEPS.map((_, i) => {
					const start = stepStart(i);
					const appear = i === 0 ? start - 22 : stepStart(i - 1) + DOT_LEAVES + 8;
					const opacity = interpolate(frame, [appear, appear + 12], [0, 1], clamp);
					if (opacity <= 0 || frame > start + RISE_FRAMES) return null;
					const {x, y} = POSITIONS[i];
					return (
						<polygon
							key={`pad-${i}`}
							points={toPoints(footprint(x, y))}
							fill="none"
							stroke={PAD}
							strokeWidth={3}
							strokeDasharray="12 9"
							strokeLinejoin="round"
							opacity={opacity}
						/>
					);
				})}

				{/* The path the dot has already travelled. */}
				{route.slice(1).map((b, idx) => (
					<polygon key={`trk-${idx}`} points={trackSegment(route[idx], b)} fill={ACCENT} />
				))}

				{/* A ring on the floor when the dot lands. */}
				{STEPS.map((_, i) => {
					const land = stepStart(i) - (i === 0 ? 0 : ARRIVE_EARLY);
					const t = interpolate(frame, [land, land + 18], [0, 1], clamp);
					if (t <= 0 || t >= 1) return null;
					const {x, y} = POSITIONS[i];
					const c = iso(x, y, 0);
					const r = lerp(0.25, 0.85, Easing.out(Easing.cubic)(t));
					return (
						<ellipse
							key={`ring-${i}`}
							cx={c.X}
							cy={c.Y}
							rx={Math.SQRT2 * COS30 * r * UNIT}
							ry={Math.SQRT2 * 0.5 * r * UNIT}
							fill="none"
							stroke={ACCENT}
							strokeWidth={4}
							opacity={1 - t}
						/>
					);
				})}

				{dotVisible ? (
					<circle cx={dotScreen.X} cy={dotScreen.Y - 15} r={17} fill={ACCENT} stroke={CREAM} strokeWidth={5} />
				) : null}

				{drawOrder.map((i) => {
					const start = stepStart(i);
					if (frame < start) return null;
					const rise = spring({
						frame: frame - start,
						fps,
						durationInFrames: RISE_FRAMES,
						config: {damping: 14, stiffness: 160, mass: 0.6},
					});
					const iconIn = interpolate(frame - start, ICON_IN, [0, 1], {
						...clamp,
						easing: Easing.out(Easing.cubic),
					});
					return <Block key={`blk-${i}`} i={i} h={Math.max(0.001, rise * BLOCK_H)} iconIn={iconIn} />;
				})}
			</svg>

			{STEPS.map((_, i) => {
				const p = interpolate(frame - stepStart(i), LABEL_IN, [0, 1], {
					...clamp,
					easing: Easing.out(Easing.cubic),
				});
				return p > 0 ? <Label key={`lbl-${i}`} i={i} progress={p} /> : null;
			})}

			<div
				style={{
					position: 'absolute',
					left: 80,
					top: 46,
					fontFamily: 'Fraunces',
					fontWeight: 600,
					fontSize: 76,
					lineHeight: 1.05,
					letterSpacing: '-0.01em',
					color: INK,
					opacity: titleIn,
					transform: `translateY(${interpolate(titleIn, [0, 1], [12, 0])}px)`,
				}}
			>
				{TITLE}
			</div>

			<div
				style={{
					position: 'absolute',
					left: 0,
					right: 0,
					bottom: 44,
					textAlign: 'center',
					fontFamily: 'DM Sans',
					fontWeight: 700,
					fontSize: 52,
					color: MUTED,
					opacity: footerIn,
					transform: `translateY(${interpolate(footerIn, [0, 1], [12, 0])}px)`,
					whiteSpace: 'pre',
				}}
			>
				{FOOTER.split('·').map((part, idx) => (
					<React.Fragment key={idx}>
						{idx > 0 ? <span style={{color: ACCENT}}>·</span> : null}
						{part}
					</React.Fragment>
				))}
			</div>
		</AbsoluteFill>
	);
};
