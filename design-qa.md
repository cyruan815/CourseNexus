# Design QA：入口页放射粒子动效

- Source visual truth: `C:\Users\RUANCH~1\AppData\Local\Temp\codex-clipboard-1d9ee9ee-984e-4086-86cc-16e4fe7712f5.png`
- Implementation screenshot: `C:\Users\ruanchengyun\.codex\visualizations\2026\07\15\019f6787-fdaf-7a12-9ad7-d5ee6cb2c3d6\welcome-particles-spring-still.png`
- Full-view comparison: `C:\Users\ruanchengyun\.codex\visualizations\2026\07\15\019f6787-fdaf-7a12-9ad7-d5ee6cb2c3d6\welcome-particles-reference-comparison.png`
- Motion evidence: `C:\Users\ruanchengyun\.codex\visualizations\2026\07\15\019f6787-fdaf-7a12-9ad7-d5ee6cb2c3d6\welcome-particles-spring-preview.gif`
- Viewport: 2048 × 1086 for the still comparison; 1280 × 720 for motion capture.
- State: `/welcome`, light theme, pointer moved from the viewport center toward the right and then around a slow ellipse.

## Findings

- No actionable P0/P1/P2 mismatch remains for the requested particle behavior.
- Particle layout now follows the reference's radial spokes rather than visible concentric rings. Particle density is intentionally lower than the earlier CourseNexus iteration and remains subordinate to the hero content.
- The field uses a shared smoothed center to retain a roughly circular silhouette. Each particle receives only part of the center displacement and still has independent spring, damping, speed, breathing phase, and lateral drift, so the motion remains elastic rather than rigid.
- Fonts and typography: unchanged from the existing CourseNexus welcome page; this task did not ask to clone Google's typography.
- Spacing and layout rhythm: existing CourseNexus navigation, hero alignment, CTA, and responsive structure are unchanged.
- Colors and visual tokens: particles retain CourseNexus blue, teal, indigo, and purple instead of copying Google's red/blue palette; opacity remains low enough to preserve text contrast.
- Image quality and asset fidelity: the supplied CourseNexus logo assets remain unchanged; the particle field is correctly rendered as a high-DPI Canvas effect rather than a raster placeholder.
- Copy and content: unchanged from the current product page.

## Comparison history

1. Earlier implementation used shared-center motion and tangent-aligned dashes. This produced synchronized movement and obvious circular rings (P2).
2. Independent anchors, spring/damping variation, large per-particle radial breathing, and lateral drift were added. Pointer following was slowed with per-particle speed caps.
3. Full-view comparison showed the remaining ring impression came primarily from dash orientation (P2). Dashes were changed to radial orientation and distributed across lightly jittered spokes, matching the reference's visual grammar.
4. Particle count was reduced from a 2300 maximum to 1100, and the final browser capture confirmed a lighter field with the hero content unobscured.
5. A later interaction pass restored a shared smoothed center, strengthened the coordinated global radial breath to 16%, and partially transferred center movement to each particle. The transfer ratio was finally reduced to 20–35% to preserve the preferred slower pointer-follow speed while retaining the circular silhouette.

## Browser verification

- Primary interaction tested: continuous pointer movement across the particle canvas for 64 captured frames; the Canvas remained non-interactive and did not block page controls.
- Console checked: no page exceptions. The only console entry is a non-functional `favicon.ico` 404 from the existing Vite page.
- Focused-region comparison was not needed because the requested change is a full-screen background motion system; the foreground UI and supplied assets were intentionally preserved.

## Follow-up polish

- P3: color-sector boundaries could be tuned further if a closer Google palette match is desired, but the current CourseNexus palette is an intentional brand constraint.

final result: passed
