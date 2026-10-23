## UX-05E extension — consistent editor, account and private-family forms

An audit identified a remaining mismatch in the **same user's input flow**: lesson authoring used 14px editor text and a pale field, family account used 13px text and a different border, and the signed-in Profile used a third input style and button radius. This is now consolidated without introducing a React form abstraction, changing the backend API, or moving any controls.

New `--ptp-` tokens: `--ptp-form-label-size` (12px), `--ptp-form-text-size` (14px), `--ptp-form-gap` (8px), `--ptp-form-row-gap` (12px), `--ptp-field-radius` (9px), `--ptp-field-border` (#bcd6d1) and `--ptp-field-background` (#fbfcfc). Standard typed fields across the lesson editor, private family login/group forms, and Profile display-name/email field share these values, with **minimum 44px** controls. Family auth/create/verify primary submission actions and Profile Save are 13px/11px to match existing main action tokens. Buttons that *navigate backwards* (Back to sign in, recovery) and other privacy/permissions controls are not recoloured as primary submits.

Intentional exceptions: readonly email retains a distinct muted background; checkbox size and disclosure remain unchanged; password confirmation/verification and expiring invitation codes remain visible; destructive-data actions remain red; narrow mobile layout remains single-column. Family-scoreboard filter/action appearances and Speak assessment are not part of this change. Consent is still opt-in and user authorization is still server-enforced.

**Tests:** `e2e/ux05e-forms.spec.ts` checks editor labels/controls and author save on desktop and mobile, focus ring, 320px no overflow and truthful signed-out account state. The existing *real isolated two-user connected family journey* adds computed-style verification at account creation and signed-in Profile Save and continues through invitation, explicit contribution consent and member removal. All four independent final-head CI jobs remain required before merge.

---

# Path to Polish V2 — design-system foundation (UX-05D)

**Status:** implementation tranche for shared tokens and repeat-use controls, not a new visual-identity exploration. Authoritative code: `v2/frontend/src/styles.css`. Owner-approved geometric P master remains unchanged in `v2/brand-review/geometric-p/` and `v2/frontend/src/BrandMark.tsx`.

## Audit findings

The existing app had accumulated several locally authored CSS values over separate feature additions. Primary (`hero-button`/`primary-action`), secondary (`secondary-action`) and file-import (`import-button`) controls were respectively 13 px, 12 px and 12 px, with slightly different border, spacing and effective height. Main page/section headings and repeated profile/group/map panels carried literal sizing and border values. The large stylesheet also contains indispensable highly specific accessibility contrast, explicit consent/error states and responsive rules. A global redesign or wholesale replace of colour literals would increase regression risk without materially benefiting a learner.

## Shared semantic contract

Tokens live in `:root`, are prefixed `--ptp-`, and are intentionally **semantic** rather than a full 1–100 spacing scale:

| Group | Token | Contract |
|---|---|---|
| Typography | `--ptp-font-body`, `--ptp-font-display` | DM Sans for body, Outfit for headings; no downloaded font files added |
| Hierarchy | `--ptp-page-title`, `--ptp-section-title`, `--ptp-panel-title` | Stable page, section and panel headings; mobile section size remains 20px |
| Feedback | `--ptp-ink`, `--ptp-muted`, `--ptp-link` | Accessible legibility for labels, supporting copy and links |
| Surfaces | `--ptp-background`, `--ptp-surface`, `--ptp-border`, `--ptp-control-border` | Shared backgrounds/borders for repeat-use sections |
| Actions | `--ptp-primary`, `--ptp-primary-hover`, `--ptp-font-action`, `--ptp-target-size` | Primary, secondary and import controls share 13px type, 44px minimum height, 11px radius |
| Affordances | `--ptp-focus`, `--ptp-radius-control`, `--ptp-radius-panel` | Consistent keyboard focus and control/panel shape |

No custom component library or CSS-in-JS introduced; existing HTML and React actions remain exactly as before.

## Boundaries and exceptions

The 44px action minimum complements existing 44px mode and audio targets, and does **not** replace the intentionally larger Home hero or specialized record/stop buttons. The optional file-import input remains accessible. The destructive red variant remains red; password/consent/backend error surfaces retain their existing explicit context. The family sign-in/group actions and map keep authorization/security truth. Contrast-specific overrides, text colours for syllable hints and sound group colours stay untouched: they are meaningful feedback, not redundant decorative palette.

This is a small *foundation*. A later audit may migrate additional scoped selectors incrementally once screenshots and user testing establish their suitability. Do not homogenize every screen by appending cascading overrides.

## Verification

- New `v2/frontend/e2e/ux05d-design-system.spec.ts` checks actual computed button height, type and radius; existing import action; computed panel surface across Profile/Expedition/Groups; responsive heading hierarchy at 320px; and the unchanged one-dot geometric P icon.
- Existing full desktop/mobile browser and Axe suites, connected family/Speak mock, private backend, benchmark and production build remain required at the final PR SHA.
- Physical Safari/device, native-speaker/audio usefulness, provider billing, UX screenshots owner sign-off and public deployment remain deferred.
