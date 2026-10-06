// Edit this file to change what the video says. Everything else adapts.
// Keep each line short (about 14 characters) so it stays readable on a phone.

export type IconName = 'bag' | 'camera' | 'palette' | 'frame';

export type Step = {
	// One or two lines. Steps 1 and 3 sit in the lower row and have room for two;
	// steps 2 and 4 sit in the upper row and should stay on one line.
	lines: string[];
	icon: IconName;
};

export const TITLE = 'How it works';

export const STEPS: Step[] = [
	{lines: ['Place your', 'order'], icon: 'bag'},
	{lines: ['Send a photo'], icon: 'camera'},
	{lines: ['We create', 'your portrait'], icon: 'palette'},
	{lines: ['Get your files'], icon: 'frame'},
];

export const FOOTER = 'Ready in 1–3 business days  ·  1 free revision';
