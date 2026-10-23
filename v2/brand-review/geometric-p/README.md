## UX-05B revision 2 — owner-requested adjustments (2026-10-23)

**Requested:** (1) move the “Path to Polish” wordmark toward the capital P in the primary signature; (2) increase the P height in the app icon until its vertical clearances match the left and right clearances. Keep the approved geometric architectural concept, P proportions and one mint endpoint.

**Implemented exact editable assets:**
- `path-to-polish-signature.svg` is now the **complete vector lockup**, not the earlier letter-only sketch. Wordmark starts at x=352, immediately beside the rightmost P bowl at x=334.41 (17.59 SVG units gap); all lettering remains editable SVG `<text>` with Outfit/Avenir/Arial fallback. The navy path underlines the phrase and ends at a single mint dot.
- `path-to-polish-square.svg` has a larger, taller white P with the same wide bowl proportion as the signature, not a copied or shrunk wordmark. Non-background mark extents (P including dot): x=35..221 and y=35..221 inside a 256-square icon, leaving **35 units of spacing on all four sides**. Dot centre (209,209), radius 12; lower baseline ends x=185 with a clear terminal gap.
- `index.html` now previews the actual complete SVG signature and the square at 16, 24, 32, 48, 72 px. Geometry/spacing may be verified without a graphic-editor export.

This is still a **review asset**, not a change to the deployed app icon/brand favicon. Owner sign-off on final primary wordmark and icon is the next gate; production integration must occur separately with complete four-lane CI.

---

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
