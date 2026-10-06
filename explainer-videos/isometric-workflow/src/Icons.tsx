import React from 'react';
import type {IconName} from './steps';

// Each icon is drawn in a 100x100 box, then laid flat on a block's top face.
const stroke = {
	fill: 'none',
	strokeWidth: 8,
	strokeLinecap: 'round' as const,
	strokeLinejoin: 'round' as const,
};

export const Icon: React.FC<{name: IconName; color: string}> = ({name, color}) => {
	switch (name) {
		case 'bag':
			return (
				<g stroke={color} {...stroke}>
					<rect x={18} y={36} width={64} height={54} rx={7} />
					<path d="M36 50 V30 A14 14 0 0 1 64 30 V50" />
				</g>
			);
		case 'camera':
			return (
				<g stroke={color} {...stroke}>
					<rect x={12} y={33} width={76} height={52} rx={10} />
					<path d="M33 33 L40 21 H60 L67 33" />
					<circle cx={50} cy={59} r={15} />
				</g>
			);
		case 'palette':
			return (
				<g>
					<path
						d="M50 10 C74 10 92 26 92 48 C92 62 82 68 72 64 C63 60 56 66 60 75 C64 85 57 92 46 90 C24 87 8 70 8 50 C8 27 27 10 50 10 Z"
						stroke={color}
						{...stroke}
					/>
					<circle cx={29} cy={41} r={7} fill={color} />
					<circle cx={47} cy={27} r={7} fill={color} />
					<circle cx={68} cy={33} r={7} fill={color} />
					<circle cx={27} cy={64} r={7} fill={color} />
				</g>
			);
		case 'frame':
			return (
				<g>
					<rect x={16} y={10} width={68} height={80} rx={7} stroke={color} {...stroke} />
					<ellipse cx={50} cy={62} rx={14} ry={11} fill={color} />
					<circle cx={33.5} cy={46} r={6} fill={color} />
					<circle cx={44} cy={37.5} r={6} fill={color} />
					<circle cx={56} cy={37.5} r={6} fill={color} />
					<circle cx={66.5} cy={46} r={6} fill={color} />
				</g>
			);
	}
};
