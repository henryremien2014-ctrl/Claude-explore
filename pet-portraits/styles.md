# Styles, prompts and quality checks

All portraits are generated from the buyer's photo as a reference image.
Likeness is the product: a beautiful portrait that doesn't look like *their*
pet is a refund.

## Models

| Step | Model (Higgsfield) | Settings |
|---|---|---|
| Portrait | `nano_banana_pro` | reference photo as `image_references`, aspect 4:5, resolution 4k |
| Phone wallpaper | `nano_banana_pro` | same prompt and reference photo, aspect 9:16, resolution 2k |
| Fallback if likeness is off | `gpt_image_2` (edit mode, quality high) or `seedream_v4_5` | same prompt |
| Living Portrait | `kling3_0_turbo` | the 9:16 portrait as `start_image`, 5 s, 1080p |

Workflow: generate 2 drafts at 2k first. Only render the chosen one at 4k,
because 4k costs more.

## Shared likeness block (goes at the start of every prompt)

```
Use the reference photo as the exact identity of the animal. Keep the same
species and breed, the exact fur colors and markings and where they sit, the
eye color, ear shape and position, muzzle shape, and any unique features
(spots, scars, a white chest patch, a crooked ear). Do not add or remove
markings. The animal must be instantly recognizable to its owner.
```

## Style 1: Royal Portrait

The pet as a noble in a classical oil painting. This is the bestselling
pet-portrait genre on Etsy.

```
{LIKENESS}
A regal classical oil painting of this {species} posed as an 18th-century
nobleman/noblewoman, three-quarter view, wearing a {outfit: embroidered velvet
jacket with gold buttons and a lace ruff | royal cape with ermine trim and a
jeweled brooch | military officer's coat with medals}. Dark, warm painted
background with soft drapery, dramatic Rembrandt lighting, visible brush
texture, rich deep colors, museum-quality fine art. Only the animal's head is
real; the body is the costume. No text, no frame, no watermark.
```

## Style 2: Storybook Watercolor

Soft and gentle. This style also works for memorial portraits.

```
{LIKENESS}
A delicate watercolor portrait of this {species}, head and shoulders, loose
expressive washes with fine ink linework on the face and eyes, soft pastel
palette that stays faithful to the real fur colors, gentle paint blooms and
splatters fading into a warm cream paper background with visible paper
texture. Airy, heartfelt, storybook illustration. No text, no frame, no
watermark.
```

Memorial variant: add `a few soft flowers ({flower}) around the base, calm and
peaceful mood`. The name and dates are added as text in a separate step, never
by the model, so spelling is always right.

## Style 3: Animated Film Look

A bright 3D cartoon character. Never name a studio in the prompt or the listing.

```
{LIKENESS}
This {species} reimagined as the lovable main character of a modern 3D
animated feature film: big expressive eyes that keep the real eye color,
slightly stylized proportions, soft fur rendered in detail, warm cinematic
lighting, a cheerful {background: sunny garden | cozy living room | autumn
park} softly blurred behind. Friendly, joyful expression. No text, no
watermark.
```

## Seasonal: Cozy Christmas (from Nov 1)

Add to any style:
`wearing a {red knit scarf | small Santa hat | reindeer antler headband},
twinkling warm Christmas lights and a softly blurred decorated tree in the
background.`

## Living Portrait (animation) prompt

```
Subtle, lifelike motion only: the {species} slowly blinks, gently tilts its
head, ears twitch softly, fur moves slightly as if in a light breeze.
{Royal: candlelight flickers softly on the painting. | Watercolor: paint
washes shimmer gently. | Film look: background leaves sway slowly.} Static
camera, no zoom, the artwork style stays exactly the same, no new objects,
seamless calm loop.
```

Settings: `kling3_0_turbo`, start image = the approved 9:16 portrait, 5
seconds, 1080p. If the motion distorts the face, regenerate once. If it fails
again, try `seedance_2_0_mini` at 720p.

## Quality checklist (run before every delivery)

- [ ] Markings match the photo: patches, spots and colors are in the right places
- [ ] Eye color matches
- [ ] Ears have the right shape and position (up, floppy, one of each)
- [ ] Correct number of eyes, ears and legs; no warped paws or extra whiskers
- [ ] No stray text, letters, signatures or watermarks in the image
- [ ] Print file is 4:5 at 4K; the phone file is 9:16
- [ ] Living Portrait: the face doesn't warp, and the motion is subtle and loops smoothly
- [ ] Would the owner instantly say "that's my dog/cat"? If unsure, regenerate.
