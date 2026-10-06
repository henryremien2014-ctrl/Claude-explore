import type {IconName} from './Icons';

// Edit this file to change what the video says; layout and timing adapt.
// Use 2-6 steps (3-5 read best in 20 seconds). Give each step one or two short
// lines of about 14 characters so they stay readable on a phone.
// Steps 1, 3, 5 sit in the lower row; steps 2, 4, 6 sit in the upper row.
// See every icon: npx remotion still IconSheet out/icon-sheet.png

export type Step = {lines: string[]; icon: IconName};

export const TITLE = 'How it works'; // '' hides it

export const STEPS: Step[] = [
	{lines: ['Place your', 'order'], icon: 'bag'},
	{lines: ['Send a photo'], icon: 'camera'},
	{lines: ['We create', 'your portrait'], icon: 'palette'},
	{lines: ['Get your files'], icon: 'frame'},
];

export const FOOTER = 'Ready in 1–3 business days  ·  1 free revision'; // '' hides it
