// Isometric projection: x runs down-right on screen, y runs down-left, z is up.
export const COS30 = Math.cos(Math.PI / 6);

export type Pt = {X: number; Y: number};

export const makeProjector =
	(originX: number, originY: number, unit: number) =>
	(x: number, y: number, z = 0): Pt => ({
		X: originX + (x - y) * COS30 * unit,
		Y: originY + (x + y) * 0.5 * unit - z * unit,
	});

export const toPoints = (pts: Pt[]) =>
	pts.map((p) => `${p.X.toFixed(2)},${p.Y.toFixed(2)}`).join(' ');
