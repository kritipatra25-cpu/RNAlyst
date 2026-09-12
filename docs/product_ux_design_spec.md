# Product / UX Design Specification: RNA-Seq AI Agent

## 1. Information Architecture
The product is a single-page AI scientific agent workspace for bulk RNA-seq analysis, literature synthesis, and biological interpretation.

```
+-----------------------------------------------------------------------------------+
|  MINIMAL TRANSCONTINENTAL SIDEBAR (LEFT)                                          |
|  - Active & Recent Projects (e.g. OSD-678, OSD-120)                              |
|  - Saved Scientific Syntheses                                                     |
|  - New Analysis Button                                                            |
+-----------------------------------------------------------------------------------+
|  PRIMARY WORKSPACE (CENTER)                                                       |
|  - Initial State: Glowing Horizontal RNA Molecular Strand + Faint Scientific Grid  |
|  - Active State: Conversational AI Analysis Stream & Evidence-Badged Reports      |
|  - Output State: Publication-Quality Figures & Candidate Prioritization Tables    |
+-----------------------------------------------------------------------------------+
|  CENTRAL FLOATING INPUT BAR (BOTTOM-CENTER)                                       |
|  - Natural-Language Prompt Entry                                                 |
|  - Dataset / File Attachment Trigger                                              |
|  - Retroglow Active Focus State                                                   |
+-----------------------------------------------------------------------------------+
```

## 2. Screen & Workspace Layout
- **Model**: Single-page continuous application workspace (similar to ChatGPT / Gemini / Perplexity).
- **Grid Layout**: 3-zone responsive flex architecture:
  - Left Zone: Collapsible translucent navigation drawer (`260px` default width).
  - Center Zone: Primary interaction viewport (`max-width: 900px`, centered).
  - Right Zone (Optional): Contextual inspector / detailed evidence snippet slide-over (`340px`).

## 3. Design Tokens

### UI Color System (DARK + RETROGLOW + MINIMAL)
- `bg-base`: `#08090d` (Near-black obsidian space background)
- `bg-surface`: `#0f1118` (Translucent dark panel surface)
- `bg-surface-elevated`: `#161922` (Elevated card/popover surface)
- `text-primary`: `#f0f3f8` (High-legibility off-white)
- `text-secondary`: `#8b94a7` (Muted cool gray)
- `text-tertiary`: `#545d6e` (Subtle caption gray)
- `border-subtle`: `rgba(255, 255, 255, 0.08)`
- `glow-cyan`: `rgba(0, 240, 255, 0.4)`
- `glow-violet`: `rgba(160, 100, 255, 0.35)`
- `glow-magenta`: `rgba(255, 80, 200, 0.3)`
- `accent-cyan`: `#00f0ff`
- `accent-violet`: `#9d65ff`

### Faint Scientific Grid Background
- Grid cell size: `48px x 48px`
- Line color: `rgba(0, 240, 255, 0.025)`
- Gradient mask: Radial fade centered on active viewport to merge subtly into near-black edges.

### Scientific Figure Color System (SOFT PASTEL + PUBLICATION-QUALITY)
*Critical Distinction: Scientific plots DO NOT use neon retroglow. They utilize soft, publication-ready pastel palettes.*
- `deg-upregulated`: `#e07a5f` (Soft terracotta / muted coral pink)
- `deg-downregulated`: `#3d405b` / `#457b9d` (Soft dusty slate blue / steel blue)
- `deg-non-significant`: `#e0e1dd` / `#cbd5e1` (Muted soft gray)
- `heatmap-high`: `#f4a261` (Soft warm peach)
- `heatmap-mid`: `#f8f9fa` (Neutral off-white)
- `heatmap-low`: `#81b29a` (Soft sage green)
- `chart-bg`: `#ffffff` / `#fafafa` (Clean white paper container with subtle border)

## 4. Typography
- **Primary Sans**: `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `sans-serif`
- **Monospace (Data / Gene IDs / Code)**: `JetBrains Mono`, `Fira Code`, `monospace`
- **Sizes**:
  - Hero Title: `1.75rem` (`28px`), `font-weight: 600`
  - Section Headings: `1.25rem` (`20px`), `font-weight: 600`
  - Body Text: `0.9375rem` (`15px`), `line-height: 1.6`
  - Metadata / Badges: `0.75rem` (`12px`), `font-weight: 500`

## 5. Sidebar Behavior
- Translucent dark background with subtle `border-r` divider.
- Shows list of previous dataset analyses (e.g. `OSD-678 Spaceflight Light Response`, `OSD-120 Primary DE`).
- Retroglow highlight on active item (`box-shadow: 0 0 12px rgba(0, 240, 255, 0.15)`).
- Collapsible via toggle icon to yield 100% horizontal viewport focus.

## 6. Input Bar Behavior
- Positioned floating at the bottom-center of the viewport.
- Contains multiline auto-expanding textarea (`placeholder="Ask a scientific question or attach RNA-seq dataset..."`).
- Retroglow focus ring: `border-color: #00f0ff; box-shadow: 0 0 20px rgba(0, 240, 255, 0.25)`.
- Attachment button: Triggers dataset selector modal (OSD-678, OSD-120, or custom upload).
- Send action: Initiates intent parsing and particle transition sequence.

## 7. Hero RNA Visual & Particle Transition
- **Landing State**: A Canvas 2D / WebGL powered double-helix RNA strand spans horizontally across the viewport, glowing in cyan and violet retroglow. It rotates smoothly at 0.005 rad/frame.
- **Particle Dissolve Sequence**:
  1. User submits query $\rightarrow$ RNA strand rotation speeds up slightly for 300ms.
  2. RNA nucleotides dissolve into 250 individual glowing light particles.
  3. Particles drift upward and outward while fading opacity to 0 over 800ms.
  4. Workspace clears, revealing the active chat stream and faint background grid.

## 8. Result & Evidence Presentation
- AI responses present the 7-question scientific synthesis report cleanly.
- Evidence badges rendered as crisp inline pills:
  - `<span class="badge badge-observed">[OBSERVED]</span>`
  - `<span class="badge badge-statistical">[STATISTICAL]</span>`
  - `<span class="badge badge-literature">[LITERATURE-SUPPORTED]</span>`
  - `<span class="badge badge-interpretation">[INTERPRETATION]</span>`
  - `<span class="badge badge-hypothesis">[HYPOTHESIS]</span>`

## 9. Component Inventory
1. `AppLayout`: Shell containing sidebar, center workspace, and bottom input bar.
2. `RNACanvas`: Hero horizontal RNA double helix & particle explosion engine.
3. `BackgroundGrid`: Faint CSS grid pattern with radial vignette mask.
4. `InputBar`: Floating central prompt & attachment bar with retroglow outline.
5. `ChatStream`: Conversational thread displaying prompt bubbles & AI report blocks.
6. `EvidenceReportCard`: Container for 7-question synthesis with badge styling.
7. `VolcanoPlot`: SVG/Canvas publication-quality soft pastel volcano plot component.
8. `HeatmapPlot`: Soft pastel expression heatmap container.
9. `CandidateTable`: Prioritization table with sorting, filtering, and symbol mapping.
10. `DatasetSelectorModal`: Pre-flight dataset chooser popover.

## 10. Accessibility & Performance
- Full keyboard navigation (`Tab`, `Enter`, `Shift+Enter` for multiline input).
- High contrast ratio (>= 4.5:1) for body text against dark backgrounds.
- Canvas animation falls back gracefully on low-power devices.
