# Design System Specification: Vintage Digital

## 1. Overview & Creative North Star
### The Creative North Star: "The Cartographer’s Ledger"
The objective of this design system is to bridge the tactile, historical romance of early 20th-century European rail travel with the precision of a modern high-fidelity digital interface. We are not simply building a game UI; we are creating a "Digital Ledger"—a sophisticated tool for a modern strategist that feels like it was pulled from a brass-trimmed travel trunk.

The aesthetic breaks the "template" look by eschewing standard grids in favor of **intentional asymmetry**. Information density is managed through high-contrast typography scales and overlapping "ephemera" (cards and tickets) that appear to sit physically atop the parchment map.

## 2. Colors
Our palette balances the warmth of aged paper with the authoritative depth of locomotive steel.

*   **Parchment & Paper (Surfaces):** Use `surface` (#fff9ed) and `surface_container` tiers to establish the base. The map occupies the lowest level, while UI panels sit atop.
*   **Locomotive Navy (Primary):** `primary` (#142d4f) is used for high-importance interactions and the player’s primary identity.
*   **Station Ember (Secondary):** `secondary` (#9b4338) is reserved for critical alerts, AI actions, and distinctive "Europe" routes.

### The "No-Line" Rule
**Prohibit 1px solid borders for sectioning.** Boundaries must be defined solely through background color shifts or tonal transitions. To separate a player stat panel from the map, use `surface_container_low` against the `background`. If a container feels lost, use the **Layering Principle** (Section 4) rather than drawing a line.

### Surface Hierarchy & Nesting
Treat the UI as stacked sheets of fine paper. 
- **Base Layer:** `surface` (The Map).
- **Secondary Layer:** `surface_container` (Persistent sidebars).
- **Tertiary Layer:** `surface_container_high` (Active modals or card expanded states).

### The "Glass & Gradient" Rule
Floating elements (like a route-claim confirmation) should use **Glassmorphism**. Apply `surface_variant` at 80% opacity with a `backdrop-filter: blur(12px)`. For primary CTAs, apply a subtle linear gradient from `primary` to `primary_container` at a 135-degree angle to provide a "silk-printed" finish.

## 3. Typography
The typography is an editorial dialogue between the romantic past and the data-driven present.

*   **Display & Headlines (Newsreader):** A sophisticated serif used for city names, "Game Over" states, and major milestones. It conveys the "Vintage Travel" authority.
*   **Titles & Body (Work Sans):** A clean, modern sans-serif for player names and general instructions. It ensures legibility against textured backgrounds.
*   **Data & AI Labels (Space Grotesk):** This is our "Modern Digital" anchor. Use `label-md` for rollout counts, train remaining, and coordinate data. Its monospaced feel suggests the precision of AI calculation.

## 4. Elevation & Depth
We avoid "drop shadows" that look like 2000s-era web design. Depth is achieved through **Tonal Layering**.

*   **The Layering Principle:** Place a `surface_container_lowest` card on a `surface_container_low` section to create a soft, natural lift.
*   **Ambient Shadows:** For floating tickets or cards, use an extra-diffused shadow: `box-shadow: 0 12px 32px rgba(31, 28, 11, 0.08)`. The shadow color is a tint of `on_surface`, never pure black.
*   **The "Ghost Border" Fallback:** If a route needs clear definition against the map, use a 1px "Ghost Border": `outline_variant` at **15% opacity**.
*   **Glassmorphism:** Use semi-transparent `surface` tokens for the AI "Rollout" dashboard to allow the map textures to bleed through, ensuring the UI feels integrated into the world rather than an overlay.

## 5. Components

### Primary Action Button
- **Style:** `primary` background, `on_primary` text.
- **Shape:** `sm` (0.125rem) roundedness for a "stamped" look.
- **Detail:** A 1px internal inset shadow (top-down) using `primary_container` to simulate a physical press.

### AI Rollout Chips
- **Style:** Use `tertiary_container` with `on_tertiary_fixed`.
- **Typo:** `label-sm` (Space Grotesk) to emphasize the "data" nature of the AI.

### Player Stat Cards
- **Construction:** No borders. Use `surface_container_low`.
- **Spacing:** `spacing-4` (1rem) internal padding. 
- **Interaction:** On hover, shift to `surface_container_highest` and apply an **Ambient Shadow**.

### Route Indicators (The Map)
- **Occupied:** Solid color fill based on player identity.
- **Empty:** `outline_variant` "Ghost Border" at 20% opacity.
- **AI Targeted:** A pulse effect using a subtle gradient of `secondary` to `secondary_container`.

### The Ticket Stack (Custom Component)
- **Visual:** Use overlapping cards with `xl` (0.75rem) roundedness on the top corners only, mimicking a physical stack of tickets in a leather wallet. Use `surface_container_lowest` to make them pop from the parchment.

## 6. Do's and Don'ts

### Do
- Use **Asymmetry**: Offset your player panels. Let the map breathe by pushing data to the edges in "ledger-style" columns.
- Use **Space Scale 12+** (3rem+) for margins around the map to maintain a premium, high-end editorial feel.
- Ensure **Space Grotesk** is used for all "Live" data that changes frequently (scores, AI counts) to separate it from "Static" labels.

### Don't
- **Never use 100% opaque black.** Even for text, use `on_surface` (#1f1c0b) to maintain the vintage ink-on-paper look.
- **Avoid 999px pill shapes** for buttons unless they are icon-only; the "stamped" rectangular `sm` radius is more period-appropriate.
- **No Divider Lines.** If you need to separate content, use a `2.5rem` vertical gap or a subtle background color shift from `surface` to `surface_dim`.