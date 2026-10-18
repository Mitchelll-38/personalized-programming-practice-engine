# Secondary text contrast

Owner: product engineer. Purpose: make meaningful rank, status, evidence and history
text readable on its actual surfaces without changing layout, actions or estimates.
Acceptance: affected rendered text reaches at least 4.5:1 contrast, including
selected and hovered recommendation surfaces; production build and focused browser
regression pass. Dependencies: existing replay and policy UI; guide PR #67 remains
an independent documentation change. Plan before implementation: measure actual
computed colors, darken failing secondary text only, verify actual DOM surfaces.

[W3C contrast minimum guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
sets 4.5:1 for normal text. These 9-11px labels are meaningful content rather than
decoration or inactive controls. The change preserves the established palette and
spacing. It is a targeted correction, not an overall accessibility conformance audit.

The browser regression reproduced the original failures before the color change,
including selected-card concept labels at 4.13:1 and rank text at 3.13:1. Nine
text declarations now use the darker green-gray `#5f6c60`. The test resolves each
rendered element's inherited opaque surface and checks computed sRGB contrast on
initial, hover and selected cards plus the 390px layout. It covers concept support,
saving status, table headers/sequences/notes and footer identity. Screenshots stay
in ignored browser test output for desktop/mobile visual review.
