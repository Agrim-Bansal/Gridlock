# Gridlock — UI Design & Wireframes

Visual spec for the frontend. Refer to [`spec.md`](./spec.md) for architecture and API contract.

---

## 1. Dashboard Page — Primary View

The default view. This is what the judges see first.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ◉ GRIDLOCK          [ Dashboard ]  [ Data Management ]        ◐ (theme)  │
├────────────────────┬────────────────────────────────────────────────────────┤
│                    │  ┌─────────────────────────────────────────────────┐  │
│  ┌──────────────┐  │  │  📅 2026-06-20  ▾     [ Fetch Predictions ]    │  │
│  │ By Violations│  │  └─────────────────────────────────────────────────┘  │
│  │ By Impact    │  │  ┌─────────────────────────────────────────────────┐  │
│  │─────────────▼│  │  │                                                 │  │
│  │              │  │  │              M A P B O X                        │  │
│  │ 1. Silk Board│  │  │                                                 │  │
│  │    342  ●●   │  │  │        ┌──┐                                     │  │
│  │   8-9a 5-7p  │  │  │     ┌──┤██├──┐    ██ = critical (red)          │  │
│  │              │  │  │     │██│██│▓▓│    ▓▓ = high (orange)           │  │
│  │ 2. KR Puram  │  │  │     └──┤▓▓├──┘    ░░ = moderate (yellow)      │  │
│  │    287  ●    │  │  │        └──┘        ·· = low (green)            │  │
│  │   8-10a      │  │  │                                                 │  │
│  │              │  │  │                 ┌──┐                            │  │
│  │ 3. Marathah. │  │  │              ░░ │▓▓│                            │  │
│  │    251  ●    │  │  │                 └──┘                            │  │
│  │   9-11a 6-8p │  │  │                                                 │  │
│  │              │  │  │          ·· ··                                  │  │
│  │ 4. Whitefld  │  │  │          ·· ··                                  │  │
│  │    198       │  │  │                                                 │  │
│  │   5-7p       │  │  │                              ░░                │  │
│  │              │  │  │                                                 │  │
│  │ 5. Hebbal    │  │  │                                                 │  │
│  │    176       │  │  │                                                 │  │
│  │   8-9a       │  │  │                                                 │  │
│  │              │  │  │                                                 │  │
│  │      ...     │  │  └─────────────────────────────────────────────────┘  │
│  └──────────────┘  │                                                      │
├────────────────────┴──────────────────────────────────────────────────────┤
│  Model: ● Ready  •  Last trained: 20 Jun, 10:35 AM  •  3 datasets       │
└──────────────────────────────────────────────────────────────────────────┘
```

### Ranked List Row Anatomy

Each row in the side panel list:

```
┌──────────────────────────────┐
│  1   Silk Board Junction     │
│      ┌─────┐  ┌──────┐      │
│      │ 342 │  │ 94.7 │      │
│      └──▲──┘  └──▲───┘      │
│    count badge  impact badge │
│      ┌───────┐ ┌────────┐   │
│      │8-9:30a│ │5:30-7p │   │
│      └───────┘ └────────┘   │
│       peak hour chips        │
└──────────────────────────────┘

- Count badge: solid fill, severity color (green→red)
- Impact badge: outlined, always blue-toned
- Peak hour chips: small, rounded, muted background
- Active tab determines which badge is primary (larger, left-aligned)
  - "By Violations" tab:  count badge prominent, impact badge smaller
  - "By Impact" tab:      impact badge prominent, count badge smaller
```

---

## 2. Dashboard — Cell Selected (List↔Map Interaction)

When a user clicks a list item, the corresponding cell highlights on the map and a popup opens.

```
┌────────────────────┬────────────────────────────────────────────────────────┐
│                    │                                                        │
│  ┌──────────────┐  │  ┌─────────────────────────────────────────────────┐   │
│  │ By Violations│  │  │                                                 │   │
│  │ By Impact    │  │  │              M A P B O X                        │   │
│  │─────────────▼│  │  │                                                 │   │
│  │              │  │  │        ┌──┐                                     │   │
│  │▶1. Silk Board│  │  │     ┌──┤██├──┐   ┌─────────────────────────┐    │   │
│  │ ██ 342 94.7  │  │  │     │██│▓▓│▓▓│   │ Silk Board Junction     │    │   │
│  │ ███████████  │◀─┼──┼─────┤▓▓├──┘──┘   │ Cell: 4779_27984       │    │   │
│  │              │  │  │     └──┘         │ Violations: 342          │    │   │
│  │ 2. KR Puram  │  │  │                  │  Signal Jumping: 145     │    │   │
│  │    287  78.2  │  │  │                  │  Wrong Lane: 98          │    │   │
│  │              │  │  │                  │  Overspeeding: 99        │    │   │
│  │ 3. Marathah. │  │  │                  │ Congestion Impact: 94.7  │    │   │
│  │    251  71.5  │  │  │                  │ Peak: 8-9:30a, 5:30-7p  │    │   │
│  │              │  │  │                  └─────────────────────────┘    │   │
│  │      ...     │  │  │                                                 │   │
│  └──────────────┘  │  └─────────────────────────────────────────────────┘   │
│                    │                                                        │
└────────────────────┴────────────────────────────────────────────────────────┘

- Selected row: highlighted background, left accent bar, bold text
- Map cell: brighter fill + 2px outline stroke (white in dark mode, blue in light)
- Map flies to center on the selected cell at zoom ~15
- Popup anchored to the cell, shows full detail
- Clicking the map background or another list item deselects
```

---

## 3. Dashboard — Map Cell Hover

Lightweight hover tooltip distinct from the full click popup.

```
                ┌──────────────────────┐
                │ Silk Board Junction  │
     ┌──┐       │ 342 violations       │
  ┌──┤██├──┐    │ Impact: 94.7         │
  │██│██│▓▓│    └──────────────────────┘
  └──┤▓▓├──┘
     └──┘

- Hover: tooltip follows cursor, no anchor
- Shows: name (if available), violation count, impact score
- No violation breakdown or peak hours — keep it fast
- Cell fill brightens to 0.85 opacity on hover
```

---

## 4. Dashboard — Empty / Loading / Error States

### 4a. No Model Trained

```
┌────────────────────┬──────────────────────────────────────────────────────┐
│                    │                                                      │
│  ┌──────────────┐  │     ┌──────────────────────────────────────┐         │
│  │              │  │     │                                      │         │
│  │  No data     │  │     │     No predictions available.        │         │
│  │  available   │  │     │                                      │         │
│  │              │  │     │     Upload training data to get      │         │
│  │  Upload a    │  │     │     started.                         │         │
│  │  dataset to  │  │     │                                      │         │
│  │  get started │  │     │     [ Go to Data Management → ]      │         │
│  │              │  │     │                                      │         │
│  └──────────────┘  │     └──────────────────────────────────────┘         │
│                    │                                                      │
├────────────────────┴──────────────────────────────────────────────────────┤
│  Model: ○ Idle  •  No datasets uploaded                                  │
└───────────────────────────────────────────────────────────────────────────┘

- Map still shows (Bengaluru, no overlay), but grayed out slightly
- Centered card with CTA pointing to Data Management
- Side panel shows matching empty state
```

### 4b. Model Training In Progress

```
┌────────────────────┬──────────────────────────────────────────────────────┐
│                    │  ┌─────────────────────────────────────────────┐     │
│  ┌──────────────┐  │  │  📅 2026-06-20  ▾     [ Fetch ⟳ ] (dim)   │     │
│  │              │  │  └─────────────────────────────────────────────┘     │
│  │  Previous    │  │  ┌─────────────────────────────────────────────┐     │
│  │  results     │  │  │                                             │     │
│  │  shown if    │  │  │   (previous predictions still visible       │     │
│  │  available,  │  │  │    but slightly dimmed)                     │     │
│  │  else empty  │  │  │                                             │     │
│  │              │  │  │                                             │     │
│  └──────────────┘  │  └─────────────────────────────────────────────┘     │
│                    │                                                      │
├────────────────────┴──────────────────────────────────────────────────────┤
│  Model: ◐ Training...  •  Last trained: 20 Jun, 10:35 AM  •  3 datasets │
└───────────────────────────────────────────────────────────────────────────┘

- "Fetch Predictions" button disabled, shows spinner icon
- Status bar pill pulses amber
- Previous predictions remain visible (dimmed) if available — don't blank the screen
```

### 4c. API Error

```
┌───────────────────────────────────────────────────────────────────────────┐
│  ⚠ Failed to fetch predictions. Check backend connection.   [ Retry ]   │
├────────────────────┬──────────────────────────────────────────────────────┤
│                    │                                                      │
│  (side panel)      │  (map with last known data, or empty)               │
│                    │                                                      │
└────────────────────┴──────────────────────────────────────────────────────┘

- Dismissible error banner at the top of the content area, below the nav bar
- Banner: warm amber background (not aggressive red), retry button on right
- Previous data stays visible if available
```

### 4d. No Hotspots for Selected Date

```
┌────────────────────┬──────────────────────────────────────────────────────┐
│                    │  ┌─────────────────────────────────────────────┐     │
│  ┌──────────────┐  │  │  📅 2026-12-25  ▾     [ Fetch Predictions ] │     │
│  │              │  │  └─────────────────────────────────────────────┘     │
│  │  No hotspots │  │  ┌─────────────────────────────────────────────┐     │
│  │  predicted   │  │  │                                             │     │
│  │  for this    │  │  │   (clean map, no overlay)                   │     │
│  │  date.       │  │  │                                             │     │
│  │              │  │  │      No violations predicted for            │     │
│  │  Try another │  │  │      December 25, 2026.                     │     │
│  │  date.       │  │  │                                             │     │
│  └──────────────┘  │  └─────────────────────────────────────────────┘     │
│                    │                                                      │
└────────────────────┴──────────────────────────────────────────────────────┘

- Not an error — just no data. Calm, informational tone.
```

---

## 5. Data Management Page

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ◉ GRIDLOCK          [ Dashboard ]  [ Data Management ]        ◐ (theme)  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Upload Training Data                                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                     │   │
│   │          ┌───┐                                                      │   │
│   │          │ ↑ │   Drag & drop a .csv file here                       │   │
│   │          └───┘   or click to browse                                 │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   Uploaded Datasets                                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  File Name              Uploaded        Rows     Status     Action  │   │
│   │─────────────────────────────────────────────────────────────────────│   │
│   │  traffic_jan2024.csv    20 Jun 10:30   15,420   ● Active    🗑     │   │
│   │  traffic_feb2024.csv    20 Jun 10:32   12,850   ● Active    🗑     │   │
│   │  traffic_mar2024.csv    20 Jun 10:45   18,200   ◐ Processing       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Model: ◐ Training...  •  Last trained: 20 Jun, 10:35 AM  •  3 datasets   │
└─────────────────────────────────────────────────────────────────────────────┘

- Full-width layout (no side panel on this page)
- Upload zone: dashed border, becomes solid blue on dragover
- Dataset table: clean rows, status pills, delete icon (with confirmation)
- Processing rows: delete disabled, spinner in status column
```

---

## 6. Data Management — CSV Preview Before Upload

After a file is selected but before confirming upload:

```
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                     │   │
│   │   📄 traffic_apr2024.csv  (2.4 MB)                      [ ✕ ]      │   │
│   │                                                                     │   │
│   │   Preview (first 5 rows):                                           │   │
│   │   ┌────────────┬───────────┬──────────┬──────────────┬───────────┐  │   │
│   │   │ timestamp  │ latitude  │ longitude│ violation    │ severity  │  │   │
│   │   ├────────────┼───────────┼──────────┼──────────────┼───────────┤  │   │
│   │   │ 2024-04-01 │ 12.9170   │ 77.6230  │ Signal Jump  │ high      │  │   │
│   │   │ 2024-04-01 │ 12.9352   │ 77.6245  │ Wrong Lane   │ moderate  │  │   │
│   │   │ 2024-04-01 │ 12.9784   │ 77.5712  │ Overspeeding │ critical  │  │   │
│   │   │ ...        │ ...       │ ...      │ ...          │ ...       │  │   │
│   │   └────────────┴───────────┴──────────┴──────────────┴───────────┘  │   │
│   │                                                                     │   │
│   │                          [ Cancel ]   [ Upload & Train → ]          │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │

- Replaces the drag-and-drop zone after file selection
- Parsed client-side with papaparse (never sent to backend yet)
- "Upload & Train" is the primary action (filled button)
- "Cancel" resets back to the drag-and-drop zone
- ✕ in the corner also cancels
```

---

## 7. Cell Popup — Full Detail (Click)

```
┌────────────────────────────────┐
│  Silk Board Junction           │
│  Cell: 4779_27984             │
│────────────────────────────────│
│  Violations        342         │
│    Signal Jumping   145        │
│    Wrong Lane        98        │
│    Overspeeding      99        │
│────────────────────────────────│
│  Congestion Impact  94.7 / 100 │
│────────────────────────────────│
│  Peak Hours                    │
│   ┌────────┐ ┌─────────┐      │
│   │8-9:30a │ │5:30-7p  │      │
│   │ ~85    │ │ ~120    │      │
│   └────────┘ └─────────┘      │
│  expected violations per window│
└────────────────────────────────┘

- Anchored to the cell on the map (Mapbox popup)
- Compact, scannable, no horizontal scroll
- Violation types as an indented sub-list
- Peak hour windows as chips with expected count below
- Popup closes on clicking map background or another cell
```

---

## 8. Status Bar Detail

Always visible at the bottom of every page.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Model: ● Ready  •  Last trained: 20 Jun, 10:35 AM  •  3 datasets     │
└─────────────────────────────────────────────────────────────────────────┘

Status pill states:
  ○ Idle       — gray, no model trained
  ◐ Training   — amber, pulsing animation
  ● Ready      — green, model is current

- Clicking "3 datasets" navigates to Data Management
- "Last trained" shows relative time on hover ("2 hours ago")
```

---

## 9. Color System

### 9.1 Severity Palette (Map + Badges)

| Severity | Fill Color | Hex (dark mode) | Usage |
|----------|-----------|-----------------|-------|
| Low | Green | `#22c55e` / 60% opacity | Bottom 40% of violation counts |
| Moderate | Yellow | `#eab308` / 60% opacity | 40th–70th percentile |
| High | Orange | `#f97316` / 60% opacity | 70th–90th percentile |
| Critical | Red | `#ef4444` / 60% opacity | Top 10% |

### 9.2 UI Accent Colors

| Element | Dark Mode | Light Mode |
|---------|-----------|------------|
| Primary accent | `blue-400` (#60a5fa) | `blue-600` (#2563eb) |
| Background | `slate-900` (#0f172a) | `white` (#ffffff) |
| Card / panel | `slate-800` (#1e293b) | `gray-50` (#f9fafb) |
| Text primary | `slate-100` (#f1f5f9) | `slate-900` (#0f172a) |
| Text secondary | `slate-400` (#94a3b8) | `slate-500` (#64748b) |
| Border | `slate-700` (#334155) | `gray-200` (#e5e7eb) |
| Error banner bg | `amber-900/50` | `amber-50` |
| Selected row bg | `blue-900/30` | `blue-50` |

---

## 10. Interaction Summary

| Trigger | Action |
|---------|--------|
| Click list row | Highlight row, fly map to cell, open popup, outline cell |
| Click map cell | Open popup, highlight corresponding list row, scroll to it |
| Hover map cell | Lightweight tooltip (name + count + impact), brighten fill |
| Click map background | Deselect everything |
| Change date + Fetch | Clear current overlay, show loading, render new predictions |
| Switch ranking tab | Re-sort the list, map overlay unchanged |
| Click "3 datasets" in status bar | Navigate to Data Management |
| Drag file onto upload zone | Show preview, enable "Upload & Train" |
