import {STEPS} from './steps';

// All timing lives here. 30 fps x 600 frames = 20 seconds.
export const FPS = 30;
export const DURATION_IN_FRAMES = 600;
export const WIDTH = 1920;
export const HEIGHT = 1080;

const N = STEPS.length;
export const FIRST_STEP_AT = 30; // block 1 starts rising at 1.0 s
const LAST_STEP_AT = 408; // the last block rises at 13.6 s, whatever the step count
// Frames from one block rising to the next (126 = 4.2 s for 4 steps).
export const STEP_EVERY = N > 1 ? Math.floor((LAST_STEP_AT - FIRST_STEP_AT) / (N - 1)) : 0;

// Offsets inside one step, in frames from the moment its block starts rising.
export const RISE_FRAMES = 24;
export const ICON_IN = [16, 30] as const;
export const LABEL_IN = [22, 38] as const;
const TRAVEL = Math.round(Math.min(48, Math.max(22, (STEP_EVERY * 2) / 7)));
export const DOT_LEAVES = STEP_EVERY - TRAVEL; // the dot sets off for the next block...
export const ARRIVE_EARLY = 4; // ...and lands this many frames before that block rises

export const TITLE_IN = [0, 16] as const;
export const FOOTER_IN = [LAST_STEP_AT + 58, LAST_STEP_AT + 78] as const;

export const stepStart = (i: number) => FIRST_STEP_AT + i * STEP_EVERY;
