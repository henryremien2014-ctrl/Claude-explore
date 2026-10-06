import React from 'react';
import {AbsoluteFill} from 'remotion';
import './fonts';
import {ICON_NAMES} from './Icons';
import {IsoBlock} from './IsoBlock';
import {makeProjector} from './iso';
import {COLORS, FONTS} from './theme';
import {HEIGHT, WIDTH} from './timeline';

// A still that shows every icon on a block, for picking icons:
// npx remotion still IconSheet out/icon-sheet.png
const COLS = 7;
const CELL_W = WIDTH / COLS;
const ROWS = Math.ceil(ICON_NAMES.length / COLS);
const CELL_H = HEIGHT / ROWS;
const UNIT = 76;

export const IconSheet: React.FC = () => (
	<AbsoluteFill style={{backgroundColor: COLORS.background}}>
		<svg width={WIDTH} height={HEIGHT}>
			{ICON_NAMES.map((name, i) => {
				const cx = (i % COLS) * CELL_W + CELL_W / 2;
				const cy = Math.floor(i / COLS) * CELL_H + CELL_H * 0.5;
				return (
					<IsoBlock
						key={name}
						iso={makeProjector(cx, cy, UNIT)}
						x={0}
						y={0}
						half={0.5}
						h={0.4}
						unit={UNIT}
						iconSize={0.76}
						icon={name}
						iconIn={1}
					/>
				);
			})}
		</svg>
		{ICON_NAMES.map((name, i) => (
			<div
				key={name}
				style={{
					position: 'absolute',
					left: (i % COLS) * CELL_W,
					width: CELL_W,
					top: Math.floor(i / COLS) * CELL_H + CELL_H * 0.5 + UNIT * 0.55,
					textAlign: 'center',
					fontFamily: FONTS.label.family,
					fontWeight: Number(FONTS.label.weight),
					fontSize: 26,
					color: COLORS.ink,
				}}
			>
				{name}
			</div>
		))}
	</AbsoluteFill>
);
