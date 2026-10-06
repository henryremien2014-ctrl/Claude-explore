import React from 'react';

// Every icon is drawn in a 100x100 box with bold strokes, then laid flat on a
// block's top face (its "up" points to the upper left). Add your own in the
// same box and list its name in ICON_NAMES.
export const ICON_NAMES = [
	'bag', 'cart', 'card', 'money', 'camera', 'upload', 'download',
	'document', 'mail', 'chat', 'phone', 'calendar', 'clock', 'palette',
	'pencil', 'scissors', 'sparkle', 'gear', 'search', 'eye', 'chart',
	'check', 'heart', 'star', 'user', 'lock', 'mic', 'headphones',
	'play', 'send', 'globe', 'home', 'truck', 'frame', 'paw',
	'sliders', 'broadcast', 'call',
] as const;

export type IconName = (typeof ICON_NAMES)[number];

const line = {
	fill: 'none',
	strokeWidth: 8,
	strokeLinecap: 'round' as const,
	strokeLinejoin: 'round' as const,
};

const starPoints = (cx: number, cy: number, outer: number, inner: number) =>
	Array.from({length: 10}, (_, k) => {
		const r = k % 2 === 0 ? outer : inner;
		const a = -Math.PI / 2 + (k * Math.PI) / 5;
		return `${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`;
	}).join(' ');

const gearPoints = (cx: number, cy: number, outer: number, inner: number, teeth = 8) =>
	Array.from({length: teeth}, (_, k) => {
		const a = (k * 2 * Math.PI) / teeth;
		return [
			[inner, a - 0.3],
			[outer, a - 0.17],
			[outer, a + 0.17],
			[inner, a + 0.3],
		]
			.map(([r, t]) => `${(cx + r * Math.cos(t)).toFixed(2)},${(cy + r * Math.sin(t)).toFixed(2)}`)
			.join(' ');
	}).join(' ');

export const Icon: React.FC<{name: IconName; color: string}> = ({name, color: c}) => {
	switch (name) {
		case 'bag':
			return (
				<g stroke={c} {...line}>
					<rect x={18} y={36} width={64} height={54} rx={7} />
					<path d="M36 50 V30 A14 14 0 0 1 64 30 V50" />
				</g>
			);
		case 'cart':
			return (
				<g stroke={c} {...line}>
					<path d="M10 20 H24 L34 64 H76 L86 32 H28" />
					<circle cx={40} cy={80} r={6} />
					<circle cx={70} cy={80} r={6} />
				</g>
			);
		case 'card':
			return (
				<g stroke={c} {...line}>
					<rect x={10} y={22} width={80} height={56} rx={8} />
					<path d="M10 40 H90" strokeWidth={10} />
					<path d="M24 62 H44" />
				</g>
			);
		case 'money':
			return (
				<g stroke={c} {...line}>
					<rect x={8} y={26} width={84} height={48} rx={6} />
					<circle cx={50} cy={50} r={11} />
					<path d="M22 42 V58 M78 42 V58" />
				</g>
			);
		case 'camera':
			return (
				<g stroke={c} {...line}>
					<rect x={12} y={33} width={76} height={52} rx={10} />
					<path d="M33 33 L40 21 H60 L67 33" />
					<circle cx={50} cy={59} r={15} />
				</g>
			);
		case 'upload':
			return (
				<g stroke={c} {...line}>
					<path d="M16 62 V82 H84 V62" />
					<path d="M50 68 V18 M32 36 L50 18 L68 36" />
				</g>
			);
		case 'download':
			return (
				<g stroke={c} {...line}>
					<path d="M16 62 V82 H84 V62" />
					<path d="M50 16 V64 M32 46 L50 64 L68 46" />
				</g>
			);
		case 'document':
			return (
				<g stroke={c} {...line}>
					<path d="M24 10 H58 L76 28 V90 H24 Z" />
					<path d="M58 10 V28 H76" />
					<path d="M36 48 H64 M36 62 H64 M36 76 H54" />
				</g>
			);
		case 'mail':
			return (
				<g stroke={c} {...line}>
					<rect x={12} y={24} width={76} height={54} rx={7} />
					<path d="M14 28 L50 56 L86 28" />
				</g>
			);
		case 'chat':
			return (
				<g stroke={c} {...line}>
					<path d="M14 18 H86 V66 H46 L26 84 V66 H14 Z" />
					<path d="M30 36 H70 M30 50 H56" />
				</g>
			);
		case 'phone':
			return (
				<g stroke={c} {...line}>
					<rect x={28} y={8} width={44} height={84} rx={9} />
					<path d="M43 19 H57 M44 80 H56" />
					<path d="M38 40 H62 M38 54 H56" strokeWidth={6} />
				</g>
			);
		case 'calendar':
			return (
				<g stroke={c} {...line}>
					<rect x={14} y={20} width={72} height={66} rx={8} />
					<path d="M14 40 H86 M34 12 V26 M66 12 V26" />
					<rect x={54} y={54} width={16} height={16} rx={2} fill={c} stroke="none" />
				</g>
			);
		case 'clock':
			return (
				<g stroke={c} {...line}>
					<circle cx={50} cy={50} r={38} />
					<path d="M50 26 V50 L66 60" />
				</g>
			);
		case 'palette':
			return (
				<g>
					<path
						d="M50 10 C74 10 92 26 92 48 C92 62 82 68 72 64 C63 60 56 66 60 75 C64 85 57 92 46 90 C24 87 8 70 8 50 C8 27 27 10 50 10 Z"
						stroke={c}
						{...line}
					/>
					<circle cx={29} cy={41} r={7} fill={c} />
					<circle cx={47} cy={27} r={7} fill={c} />
					<circle cx={68} cy={33} r={7} fill={c} />
					<circle cx={27} cy={64} r={7} fill={c} />
				</g>
			);
		case 'pencil':
			return (
				<g stroke={c} {...line}>
					<path d="M12 30 L30 12 L74 56 L86 86 L56 74 Z" />
					<path d="M56 74 L74 56 M21 39 L39 21" />
				</g>
			);
		case 'scissors':
			return (
				<g stroke={c} {...line}>
					<circle cx={30} cy={72} r={12} />
					<circle cx={70} cy={72} r={12} />
					<path d="M38 63 L76 14 M62 63 L24 14" />
				</g>
			);
		case 'sparkle':
			return (
				<g stroke={c} {...line}>
					<path d="M50 6 C54 36 64 46 94 50 C64 54 54 64 50 94 C46 64 36 54 6 50 C36 46 46 36 50 6 Z" />
				</g>
			);
		case 'gear':
			return (
				<g stroke={c} {...line}>
					<polygon points={gearPoints(50, 50, 42, 31)} />
					<circle cx={50} cy={50} r={12} />
				</g>
			);
		case 'search':
			return (
				<g stroke={c} {...line}>
					<circle cx={42} cy={42} r={26} />
					<path d="M62 62 L86 86" />
				</g>
			);
		case 'eye':
			return (
				<g stroke={c} {...line}>
					<path d="M8 50 C24 24 76 24 92 50 C76 76 24 76 8 50 Z" />
					<circle cx={50} cy={50} r={12} fill={c} />
				</g>
			);
		case 'chart':
			return (
				<g stroke={c} {...line}>
					<path d="M14 14 V86 H88" />
					<path d="M34 74 V58 M52 74 V42 M70 74 V26" strokeWidth={11} strokeLinecap="butt" />
				</g>
			);
		case 'check':
			return (
				// Drawn pre-rotated so it reads as a tick, not an L, once laid flat.
				<path d="M30 36 L18 74 L96 38" stroke={c} {...line} strokeWidth={12} />
			);
		case 'heart':
			return (
				<path
					d="M50 84 C22 64 12 46 22 31 C31 18 45 21 50 33 C55 21 69 18 78 31 C88 46 78 64 50 84 Z"
					stroke={c}
					{...line}
				/>
			);
		case 'star':
			return <polygon points={starPoints(50, 54, 40, 17)} stroke={c} {...line} />;
		case 'user':
			return (
				// Turned 45 degrees so the head sits above the shoulders on screen.
				<g stroke={c} {...line} transform="rotate(45 50 50)">
					<circle cx={50} cy={30} r={16} />
					<path d="M18 86 C18 58 82 58 82 86 Z" />
				</g>
			);
		case 'lock':
			return (
				<g stroke={c} {...line}>
					<rect x={20} y={44} width={60} height={44} rx={8} />
					<path d="M34 44 V32 A16 16 0 0 1 66 32 V44" />
				</g>
			);
		case 'mic':
			return (
				<g stroke={c} {...line}>
					<rect x={37} y={10} width={26} height={46} rx={13} />
					<path d="M24 44 A26 26 0 0 0 76 44" />
					<path d="M50 70 V88 M36 88 H64" />
				</g>
			);
		case 'headphones':
			return (
				<g stroke={c} {...line}>
					<path d="M18 64 V52 A32 32 0 0 1 82 52 V64" />
					<rect x={12} y={58} width={18} height={28} rx={6} />
					<rect x={70} y={58} width={18} height={28} rx={6} />
				</g>
			);
		case 'play':
			return (
				<g>
					<rect x={10} y={20} width={80} height={60} rx={12} stroke={c} {...line} />
					<path d="M42 36 L66 50 L42 64 Z" fill={c} stroke={c} strokeWidth={4} strokeLinejoin="round" />
				</g>
			);
		case 'send':
			return (
				<g stroke={c} {...line}>
					<path d="M10 46 L88 12 L64 88 L46 56 Z" />
					<path d="M46 56 L88 12" />
				</g>
			);
		case 'globe':
			return (
				<g stroke={c} {...line}>
					<circle cx={50} cy={50} r={38} />
					<ellipse cx={50} cy={50} rx={16} ry={38} />
					<path d="M12 50 H88" />
				</g>
			);
		case 'home':
			return (
				<g stroke={c} {...line}>
					<path d="M12 48 L50 14 L88 48" />
					<path d="M24 38 V86 H76 V38" />
					<path d="M42 86 V64 H58 V86" />
				</g>
			);
		case 'truck':
			return (
				<g stroke={c} {...line}>
					<path d="M8 24 H58 V64 H8 Z" />
					<path d="M58 38 H76 L90 54 V64 H58" />
					<circle cx={26} cy={76} r={8} />
					<circle cx={74} cy={76} r={8} />
				</g>
			);
		case 'frame':
			return (
				<g>
					<rect x={16} y={10} width={68} height={80} rx={7} stroke={c} {...line} />
					<ellipse cx={50} cy={62} rx={14} ry={11} fill={c} />
					<circle cx={33.5} cy={46} r={6} fill={c} />
					<circle cx={44} cy={37.5} r={6} fill={c} />
					<circle cx={56} cy={37.5} r={6} fill={c} />
					<circle cx={66.5} cy={46} r={6} fill={c} />
				</g>
			);
		case 'paw':
			return (
				<g fill={c}>
					<ellipse cx={50} cy={66} rx={19} ry={15} />
					<circle cx={24} cy={44} r={9} />
					<circle cx={40} cy={28} r={9} />
					<circle cx={60} cy={28} r={9} />
					<circle cx={76} cy={44} r={9} />
				</g>
			);
		case 'sliders':
			return (
				// Three mixing-desk faders; the bold knobs carry the shape.
				<g>
					<path d="M24 12 V88 M50 12 V88 M76 12 V88" stroke={c} {...line} />
					<rect x={12} y={56} width={24} height={18} rx={5} fill={c} />
					<rect x={38} y={24} width={24} height={18} rx={5} fill={c} />
					<rect x={64} y={44} width={24} height={18} rx={5} fill={c} />
				</g>
			);
		case 'broadcast':
			return (
				// "On air": a dot with signal arcs either side, turned 45 degrees so
				// the arcs sit left and right of the dot on screen.
				<g transform="rotate(45 50 50)">
					<circle cx={50} cy={50} r={11} fill={c} />
					<g stroke={c} {...line}>
						<path d="M68.4 34.6 A24 24 0 0 1 68.4 65.4 M31.6 34.6 A24 24 0 0 0 31.6 65.4" />
						<path d="M78.3 21.7 A40 40 0 0 1 78.3 78.3 M21.7 21.7 A40 40 0 0 0 21.7 78.3" />
					</g>
				</g>
			);
		case 'call':
			return (
				// A telephone handset, filled so it stays bold when laid flat.
				<path
					d="M30 12 C22 12 12 20 14 32 C18 58 42 82 68 86 C80 88 88 80 88 70 V62 L68 54 L58 66 C46 60 40 54 34 42 L46 32 L38 12 Z"
					fill={c}
					stroke={c}
					strokeWidth={4}
					strokeLinejoin="round"
				/>
			);
	}
};
