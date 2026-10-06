import React from 'react';
import {Composition} from 'remotion';
import {HowItWorks} from './HowItWorks';
import {DURATION_IN_FRAMES, FPS, HEIGHT, WIDTH} from './timeline';

export const RemotionRoot: React.FC = () => {
	return (
		<Composition
			id="HowItWorks"
			component={HowItWorks}
			durationInFrames={DURATION_IN_FRAMES}
			fps={FPS}
			width={WIDTH}
			height={HEIGHT}
		/>
	);
};
