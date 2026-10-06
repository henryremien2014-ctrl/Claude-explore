// Colours, fonts and text sizes. Swap these for a client's brand.
export const COLORS = {
	background: '#F5EFE4', // warm paper
	grid: '#E2D7C5', // faint, static isometric dot grid
	ink: '#24201C', // title and labels
	muted: '#5F564C', // footer
	accent: '#CF633D', // the dot, its trail and the step numbers
	cream: '#FBF7EF', // icons and the numbers inside the badges
	pad: '#BFAE93', // dashed outline where the next block will rise
	top: '#4F968B', // block faces, lightest...
	left: '#3D7B72',
	right: '#2F635C', // ...to darkest
	edge: '#72B2A7', // thin highlight around each top face
};

export const SHOW_GRID = true;

// Font files live in public/fonts. For another font: npm i -D @fontsource/<name>,
// then copy node_modules/@fontsource/<name>/files/<name>-latin-<weight>-normal.woff2.
export const FONTS = {
	label: {family: 'DM Sans', weight: '700', file: 'fonts/dm-sans-700.woff2'},
	number: {family: 'DM Sans', weight: '800', file: 'fonts/dm-sans-800.woff2'},
	title: {family: 'Fraunces', weight: '600', file: 'fonts/fraunces-600.woff2'},
};

// Sizes in px on the 1920x1080 frame. A 68 px label shows at about 13.8 pt on
// a phone held upright (390 pt wide); keep labels at 60 px or more.
export const LABEL_SIZE = 68;
export const TITLE_SIZE = 76;
export const FOOTER_SIZE = 60; // 12.2 pt upright: the footer often carries the promise
