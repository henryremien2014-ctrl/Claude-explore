import React, {useEffect, useMemo, useState} from 'react';
import {
	AbsoluteFill,
	Easing,
	interpolate,
	spring,
	useCurrentFrame,
	useDelayRender,
	useVideoConfig,
} from 'remotion';
import {fontsReady} from './fonts';
import {IsoBlock} from './IsoBlock';
import {COS30, toPoints} from './iso';
import {
	BADGE,
	BADGE_GAP,
	BLOCK_H,
	HALF,
	ICON_SIZE,
	LABEL_LEADING,
	LABEL_PX,
	N,
	POSITIONS,
	TRACK_W,
	UNIT,
	isUpper,
	iso,
	labelAnchorY,
	placeLabels,
} from './layout';
import {FOOTER, STEPS, TITLE} from './steps';
import {COLORS, FONTS, FOOTER_SIZE, SHOW_GRID, TITLE_SIZE} from './theme';
import {
	ARRIVE_EARLY,
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

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// Width of a label (badge + longest line), measured with the real font.
const measureLabel = (lines: string[]) => {
	const ctx = document.createElement('canvas').getContext('2d');
	if (!ctx) throw new Error('No 2D canvas available to measure labels.');
	ctx.font = `${FONTS.label.weight} ${LABEL_PX}px "${FONTS.label.family}"`;
	ctx.letterSpacing = `${-0.01 * LABEL_PX}px`;
	return BADGE + BADGE_GAP + Math.max(...lines.map((l) => ctx.measureText(l).width));
};

// Points along the route, in iso units, from block 1 up to `progress`
// (progress = segment index + fraction along it).
const routeTo = (progress: number) => {
	const pts = [POSITIONS[0]];
	const whole = Math.floor(progress);
	for (let i = 1; i <= whole && i < N; i++) pts.push(POSITIONS[i]);
	const frac = progress - whole;
	if (frac > 0 && whole + 1 < N) {
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

const footprint = (x: number, y: number) => [
	iso(x - HALF, y - HALF),
	iso(x + HALF, y - HALF),
	iso(x + HALF, y + HALF),
	iso(x - HALF, y + HALF),
];

const Label: React.FC<{i: number; left: number; progress: number}> = ({i, left, progress}) => {
	const upper = isUpper(i);
	const shift = interpolate(progress, [0, 1], [upper ? 14 : -14, 0]);
	return (
		<div
			style={{
				position: 'absolute',
				left,
				top: labelAnchorY(i),
				transform: `translateY(${upper ? '-100%' : '0%'}) translateY(${shift}px)`,
				opacity: progress,
				display: 'flex',
				alignItems: 'flex-start',
				gap: BADGE_GAP,
				whiteSpace: 'nowrap',
			}}
		>
			<div
				style={{
					width: BADGE,
					height: BADGE,
					marginTop: (LABEL_PX * LABEL_LEADING - BADGE) / 2,
					borderRadius: BADGE / 2,
					background: COLORS.accent,
					color: COLORS.cream,
					fontFamily: FONTS.number.family,
					fontWeight: Number(FONTS.number.weight),
					fontSize: Math.max(46, Math.round(LABEL_PX * 0.68)), // >= 9.4 pt on an upright phone
					lineHeight: `${BADGE}px`,
					textAlign: 'center',
					flexShrink: 0,
				}}
			>
				{i + 1}
			</div>
			<div
				style={{
					fontFamily: FONTS.label.family,
					fontWeight: Number(FONTS.label.weight),
					fontSize: LABEL_PX,
					lineHeight: LABEL_LEADING,
					letterSpacing: '-0.01em',
					color: COLORS.ink,
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
	const {delayRender, continueRender, cancelRender} = useDelayRender();

	// Measure label widths once the real font has loaded, then place them.
	const [handle] = useState(() => delayRender('Measuring label widths'));
	const [lefts, setLefts] = useState<number[] | null>(null);
	useEffect(() => {
		fontsReady
			.then(() => {
				setLefts(placeLabels(STEPS.map((s) => measureLabel(s.lines))));
				continueRender(handle);
			})
			.catch((err) => cancelRender(err));
	}, [handle, continueRender, cancelRender]);

	// Faint isometric dot grid: static "graph paper" under the scene.
	const gridDots = useMemo(() => {
		if (!SHOW_GRID) return [];
		const dots: {X: number; Y: number}[] = [];
		for (let gx = -30; gx <= 30; gx += 0.5) {
			for (let gy = -36; gy <= 24; gy += 0.5) {
				const p = iso(gx, gy, 0);
				if (p.X > -10 && p.X < WIDTH + 10 && p.Y > -10 && p.Y < HEIGHT + 10) dots.push(p);
			}
		}
		return dots;
	}, []);

	const ease = Easing.inOut(Easing.cubic);

	// How far the dot has travelled along the route (segment index + fraction).
	let progress = 0;
	let dotVisible = false;
	for (let i = 0; i < N - 1; i++) {
		const leave = stepStart(i) + DOT_LEAVES;
		const arrive = stepStart(i + 1) - ARRIVE_EARLY;
		if (frame >= leave) {
			progress = i + interpolate(frame, [leave, arrive], [0, 1], {...clamp, easing: ease});
		}
		if (frame >= leave && frame <= stepStart(i + 1) + 2) dotVisible = true;
	}
	const route = routeTo(progress);
	const dotPos = route[route.length - 1];
	const dotScreen = iso(dotPos.x, dotPos.y, 0);
	const dotR = Math.max(12, UNIT * 0.11);

	const titleIn = interpolate(frame, TITLE_IN, [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
	const footerIn = interpolate(frame, FOOTER_IN, [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});

	// Back-to-front order so nearer blocks are painted over farther ones.
	const drawOrder = STEPS.map((_, i) => i).sort(
		(a, b) => POSITIONS[a].x + POSITIONS[a].y - (POSITIONS[b].x + POSITIONS[b].y),
	);

	return (
		<AbsoluteFill style={{backgroundColor: COLORS.background}}>
			<svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
				{gridDots.map((p, idx) => (
					<circle key={idx} cx={p.X} cy={p.Y} r={2.4} fill={COLORS.grid} />
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
							stroke={COLORS.pad}
							strokeWidth={3}
							strokeDasharray="12 9"
							strokeLinejoin="round"
							opacity={opacity}
						/>
					);
				})}

				{/* The path the dot has already travelled. */}
				{route.slice(1).map((b, idx) => (
					<polygon key={`trk-${idx}`} points={trackSegment(route[idx], b)} fill={COLORS.accent} />
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
							stroke={COLORS.accent}
							strokeWidth={4}
							opacity={1 - t}
						/>
					);
				})}

				{dotVisible ? (
					<circle
						cx={dotScreen.X}
						cy={dotScreen.Y - dotR + 2}
						r={dotR}
						fill={COLORS.accent}
						stroke={COLORS.cream}
						strokeWidth={5}
					/>
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
					return (
						<IsoBlock
							key={`blk-${i}`}
							iso={iso}
							x={POSITIONS[i].x}
							y={POSITIONS[i].y}
							half={HALF}
							h={Math.max(0.001, rise * BLOCK_H)}
							unit={UNIT}
							iconSize={ICON_SIZE}
							icon={STEPS[i].icon}
							iconIn={iconIn}
						/>
					);
				})}
			</svg>

			{lefts
				? STEPS.map((_, i) => {
						const p = interpolate(frame - stepStart(i), LABEL_IN, [0, 1], {
							...clamp,
							easing: Easing.out(Easing.cubic),
						});
						return p > 0 ? <Label key={`lbl-${i}`} i={i} left={lefts[i]} progress={p} /> : null;
					})
				: null}

			{TITLE ? (
				<div
					style={{
						position: 'absolute',
						left: 80,
						top: 50,
						fontFamily: FONTS.title.family,
						fontWeight: Number(FONTS.title.weight),
						fontSize: TITLE_SIZE,
						lineHeight: 1.05,
						letterSpacing: '-0.01em',
						color: COLORS.ink,
						opacity: titleIn,
						transform: `translateY(${interpolate(titleIn, [0, 1], [12, 0])}px)`,
					}}
				>
					{TITLE}
				</div>
			) : null}

			{FOOTER ? (
				<div
					style={{
						position: 'absolute',
						left: 0,
						right: 0,
						bottom: 56,
						textAlign: 'center',
						fontFamily: FONTS.label.family,
						fontWeight: Number(FONTS.label.weight),
						fontSize: FOOTER_SIZE,
						color: COLORS.muted,
						opacity: footerIn,
						transform: `translateY(${interpolate(footerIn, [0, 1], [12, 0])}px)`,
						whiteSpace: 'pre',
					}}
				>
					{FOOTER.split('·').map((part, idx) => (
						<React.Fragment key={idx}>
							{idx > 0 ? <span style={{color: COLORS.accent}}>·</span> : null}
							{part}
						</React.Fragment>
					))}
				</div>
			) : null}
		</AbsoluteFill>
	);
};
