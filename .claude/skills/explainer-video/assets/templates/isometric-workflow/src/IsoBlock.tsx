import React from 'react';
import {Icon, type IconName} from './Icons';
import {COS30, type Projector, toPoints} from './iso';
import {COLORS} from './theme';

// One isometric block: three shaded faces (no shadows) and an icon lying flat
// on the top face. `h` is the current height, so animating it makes it rise.
export const IsoBlock: React.FC<{
	iso: Projector;
	x: number;
	y: number;
	half: number;
	h: number;
	unit: number;
	iconSize: number;
	icon: IconName;
	iconIn: number; // 0..1: icon opacity and scale-in
}> = ({iso, x, y, half, h, unit, iconSize, icon, iconIn}) => {
	const top = [
		iso(x - half, y - half, h),
		iso(x + half, y - half, h),
		iso(x + half, y + half, h),
		iso(x - half, y + half, h),
	];
	const right = [
		iso(x + half, y - half, 0),
		iso(x + half, y + half, 0),
		iso(x + half, y + half, h),
		iso(x + half, y - half, h),
	];
	const left = [
		iso(x - half, y + half, 0),
		iso(x + half, y + half, 0),
		iso(x + half, y + half, h),
		iso(x - half, y + half, h),
	];

	// Map the icon's 100x100 box onto the top face: icon "right" runs up-right
	// along -y, icon "down" runs down-right along +x.
	const c = iso(x, y, h);
	const k = (iconSize * unit) / 100;
	const a = k * COS30;
	const matrix = `matrix(${a} ${-k / 2} ${a} ${k / 2} ${c.X - a * 100} ${c.Y})`;
	const scale = 0.7 + 0.3 * iconIn;

	return (
		<g>
			<polygon points={toPoints(left)} fill={COLORS.left} />
			<polygon points={toPoints(right)} fill={COLORS.right} />
			<polygon
				points={toPoints(top)}
				fill={COLORS.top}
				stroke={COLORS.edge}
				strokeWidth={2}
				strokeLinejoin="round"
			/>
			{iconIn > 0 ? (
				<g transform={matrix} opacity={iconIn}>
					<g transform={`translate(50 50) scale(${scale}) translate(-50 -50)`}>
						<Icon name={icon} color={COLORS.cream} />
					</g>
				</g>
			) : null}
		</g>
	);
};
