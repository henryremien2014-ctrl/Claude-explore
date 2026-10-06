// All timing lives here (30 fps, 600 frames = 20 s).
export const FPS = 30;
export const DURATION_IN_FRAMES = 600;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const FIRST_STEP_AT = 30; // block 1 starts rising at 1.0 s
export const STEP_EVERY = 126; // a new block every 4.2 s

// Offsets inside one step, in frames from the moment its block starts rising.
export const RISE_FRAMES = 24;
export const ICON_IN = [16, 30] as const;
export const LABEL_IN = [22, 38] as const;
export const DOT_LEAVES = 90; // the dot sets off for the next block
// The dot arrives exactly when the next step starts (STEP_EVERY).

export const TITLE_IN = [0, 16] as const;
export const FOOTER_IN = [466, 486] as const;

export const stepStart = (i: number) => FIRST_STEP_AT + i * STEP_EVERY;
