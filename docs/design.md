# Design Document
## The Lenny Growth Assistant UI/UX
### Version 1.0 · Oogway Labs

---

## 1. Design Philosophy

The Lenny Growth Assistant targets high-signal, high-intent users: growth PMs and founders who are results-oriented and information-dense. The interface reflects this:

- **Clarity over decoration**: Every element earns its place
- **Density without clutter**: Pack maximum information into minimal space
- **Professional dark mode**: Matches the aesthetic of premium dev tools (Linear, Raycast, Vercel dashboard)
- **Immediate trust signals**: Citations visible inline; security badges on artifacts

---

## 2. Color Palette

### Dark Surface System
| Token | Hex | Usage |
|-------|-----|-------|
| `surface-900` | `#0a0a0f` | Page background |
| `surface-800` | `#12121a` | Secondary panels |
| `surface-700` | `#1c1c2e` | Cards |
| `surface-600` | `#232336` | Interactive elements |
| `surface-500` | `#2a2a42` | Borders, dividers |

### Brand Colors
| Token | Hex | Usage |
|-------|-----|-------|
| `brand-500` | `#6366f1` | Primary CTA, accents |
| `brand-600` | `#4f46e5` | Send button, hover states |
| `accent-500` | `#8b5cf6` | Artifact badges |
| `gold-500` | `#f59e0b` | Ship 30 feature |

### Semantic
| Color | Usage |
|-------|-------|
| `emerald-400` | Active/healthy status |
| `red-400` | Errors |
| `amber-400` | Security warnings |
| `brand-300` | Citations, links |

---

## 3. Typography

| Element | Font | Weight | Size |
|---------|------|--------|------|
| Headings | Inter | 700–800 | 16–28px |
| Body | Inter | 400 | 14px |
| Labels/badges | Inter | 500–600 | 10–12px |
| Code | JetBrains Mono | 400–500 | 12–13px |

Line height: 1.6–1.75 for prose, 1.2 for labels.

---

## 4. Layout — Split Screen

```
┌─────────────────────────────────────────────────────────────┐
│  Header Bar (fixed, 56px)                                   │
│  [Logo] [Status] ············· [Artifact Toggle] [Docs]     │
├─────────────────────────────┬───────────────────────────────┤
│                             │                               │
│   Chat Panel (50% width)    │  Artifact Panel (50% width)   │
│                             │                               │
│   ┌─────────────────────┐   │  ┌──────────────────────────┐ │
│   │  Message history    │   │  │  Header: type + tabs     │ │
│   │  (scrollable)       │   │  │  Security Badge          │ │
│   │                     │   │  │  Word Count              │ │
│   │  [User message]     │   │  ├──────────────────────────┤ │
│   │  [Assistant reply]  │   │  │                          │ │
│   │   + Citations       │   │  │   Preview / Source       │ │
│   │   + Artifact btn    │   │  │   (scrollable)           │ │
│   │                     │   │  │                          │ │
│   └─────────────────────┘   │  └──────────────────────────┘ │
│                             │                               │
│   ┌─────────────────────┐   │                               │
│   │  Input Area         │   │                               │
│   │  [Provider][Ship30] │   │                               │
│   │  [Textarea]  [Send] │   │                               │
│   └─────────────────────┘   │                               │
└─────────────────────────────┴───────────────────────────────┘
```

### Responsive Behavior
- **≥ 640px (sm)**: Split screen (50/50)
- **< 640px (mobile)**: Single panel; header button toggles between chat and artifact
- Artifact panel slides in from the right with a 300ms ease-out transition

---

## 5. Components

### 5.1 Message Bubbles

**User message**:
- Right-aligned, `brand-600` background, rounded-br-sm
- Avatar: initials "U" on brand-600

**Assistant message**:
- Left-aligned, glassmorphism card, rounded-bl-sm
- Avatar: "L" gradient (violet → indigo), glow shadow
- Markdown rendered with prose styles
- Citations below the bubble as clickable pills
- Artifact button if artifact detected

### 5.2 Citation Badges
- Pill shape, `brand-500/10` background, `brand-500/20` border
- Shows episode title (truncated to 32 chars) + similarity % score
- Links to source URL on click
- Hover: border brightens

### 5.3 Provider Selector Dropdown
- Trigger button shows emoji icon + label
- Dropdown floats above input, glassmorphism panel
- Three options: 🦙 Ollama, 🌩 Claude, ⚡ GPT-4o
- Selected item has `brand-500/15` background + checkmark

### 5.4 Ship 30 Modal
- Centered modal with backdrop blur
- `glass-bright` card, slide-up animation
- Textarea for topic input
- Generate button: gold gradient (amber → orange)

### 5.5 ArtifactViewer Tabs
- **Preview tab**: Default; renders Markdown or sandboxed HTML
- **Source tab**: Monospace raw content with line wrapping
- Active tab: `brand-500/20` background, `brand-500/30` border

### 5.6 Security Badge
- Two states:
  1. **Clean** (no flags): emerald shield + "✓ Sanitized Sandbox Mode"
  2. **Sanitized** (flags present): amber shield + "Sanitized Sandbox Mode · N issues removed"
     - Expandable: click to see each removed pattern in a sub-list

### 5.7 Word Count Progress Bar
- 16px wide bar showing progress toward 1,250-word target
- Green when 1,200–1,300 words; brand indigo otherwise
- Shows numeric count + checkmark when in target range

---

## 6. Motion & Animation

| Element | Animation | Duration | Easing |
|---------|-----------|----------|--------|
| New messages | `slideUp` (Y: 16px → 0) | 350ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Artifact panel | CSS width transition | 300ms | `ease-out` |
| Dropdowns | `slideUp` | 200ms | ease-out |
| Typing dots | `bounceDot` (scale 0→1→0) | 1.4s | ease-in-out, staggered |
| Status pulse | `pulse` | 3s | ease-in-out |
| Send button hover | box-shadow glow | 150ms | linear |
| Animated border | `borderRotate` gradient | 4s | linear, infinite |

---

## 7. Accessibility

- **Contrast**: All text/background combinations meet WCAG AA (4.5:1 minimum)
- **Focus rings**: 2px `brand-500` ring with `surface-800` offset on all interactive elements
- **ARIA labels**: `aria-label` on icon-only buttons (close, copy, send)
- **Semantic HTML**: `<main>`, proper heading hierarchy (`h1` per page), `<button>` not `<div>`
- **Keyboard navigation**: All actions reachable via Tab + Enter/Space
- **Screen reader**: iframe has `title="Sanitized HTML Artifact"` and `aria-label`

---

## 8. Empty State Design

The empty state serves as an onboarding moment:

1. **Hero icon**: Large branded square with chat bubble SVG + emerald verified dot
2. **Headline**: "Lenny Growth Assistant" with gradient on "Growth"
3. **Subtext**: One-liner describing the value proposition
4. **Suggested prompts grid**: 4 quick-start prompts as interactive cards
   - Hover: border brightens, arrow icon appears
   - One prompt opens the Ship 30 modal directly
