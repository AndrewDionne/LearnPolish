# UX-05B · Geometric P brand exploration

## Owner direction

Use the uploaded geometric capital **P**, long horizontal baseline (the path), and detached terminal dot as the basis. The earlier rounded lowercase p with a separate wavy two-node route was explicitly rejected. The owner approved further development of the architectural P concept, **not** rollout of a finished mark.

## Candidate assets

- [Primary geometric P signature](path-to-polish-signature.svg): transparent navy, custom filled geometric outlines and P counter, balanced heavy stroke, controlled baseline, smaller circular stop.
- [Compact app icon](path-to-polish-square.svg): separately drawn square-optical letter, navy rounded tile, white P with a single mint terminal. Adapted for 16–72 px and not a horizontal logo merely shrunk to fit.
- [Visual review sheet](index.html): self-contained offline view of the actual SVG assets at two scales and 16, 24, 32, 48 and 72 px.

These are deliberately **two related but different optical cuts**. Retain the existing wordmark and colour palette until there is a separate approval for broader branding. The letterform is custom geometric SVG with no purchased font, embedded typeface, gradients, and no icon library.

## Review before integration

1. Does the primary signature match the intended bold P and path concept? Check bowl curve, stem, baseline reach and spacing to dot.
2. Is the leftward short crossbar necessary? At a glance it can make the monogram resemble a currency sign (₽); that ambiguity should be explicitly accepted or resolved.
3. Does the small icon read as the same identity at 16–32 px? Check white/teal contrast and mint endpoint.
4. Keep the app's current `BrandMark.tsx`, `public/brand-mark.svg`, `index.html` and CSS **unchanged** until approval. A later integration PR would then convert the approved SVG geometry to the in-app component/favicon and pass the established four-lane CI suite.
5. Actual iPhone/Safari use, native-speaker/audio testing and owner aesthetic approval remain deferred.

No learning content, scoring, XP, permissions, user accounts, microcopy or speech provider flow is part of this design-only branch.
