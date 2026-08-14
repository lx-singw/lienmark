# 30. UI Component Design System & UX Architecture

*This document defines Lienmark's design aesthetics, visual token architecture, micro-animation guidelines, and responsive layout standards.*

---

## 🎨 1. Design Aesthetics & Visual Identity

Lienmark is engineered to deliver a **sleek, high-trust, enterprise dark-mode interface** tailored for entertainment executives, production lawyers, and studio heads.

### 1.1 Color Palette & Design Tokens

```css
:root {
  /* Surface Colors */
  --bg-primary: #0A0D14;       /* Deep obsidian black background */
  --bg-surface: #121824;       /* Glassmorphism surface container */
  --bg-surface-hover: #1E2638; /* Interactive hover elevation */
  
  /* Brand Accents */
  --accent-gold: #F59E0B;      /* Premium legal gold accent */
  --accent-cyan: #06B6D4;      /* Parallel AI agentic blue */
  --accent-emerald: #10B981;   /* Cleared / verified claim green */
  --accent-rose: #F43F5E;      /* High-risk / conflict red */
  
  /* Typography */
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-display: 'Outfit', sans-serif;
}
```

---

## ✨ 2. Key UI Components & Micro-Interactions

### 2.1 Glassmorphic Intake File Dropzone (`IntakeDropzone.tsx`)
- Sleek drag-and-drop zone with animated border gradients on drag-over.
- Real-time progress bar with step-by-step agent status indicators (*"Intake: SHA-256 Hashing $\rightarrow$ Research: Parallel Search $\rightarrow$ Risk Scoring: Rule Engine"*).

### 2.2 Proactive Toast Notification Container (`ToastContainer.tsx`)
- Glowing toast alert container surfacing background Discovery Agent notifications (Beat A) with priority color coding (`emerald` clear, `gold` stale re-review, `rose` dispute alert).

### 2.3 Interactive Clarifying Question Modal (`ClarifyingQuestionModal.tsx`)
- Modern glassmorphism modal for mid-run human legal input (Beat C), prompting counsel for specific missing parameters with pre-populated citation choices.

### 2.4 Interactive Attorney Override Modal (`AttorneyOverrideModal.tsx`)
- Split-pane layout: Left pane shows script snippet & Parallel Search API evidence; Right pane shows pre-populated legal citations (17 U.S.C. § 107) and RSA-256 digital signature canvas.

### 2.5 Feature Toggle Suite Config (`FeatureTogglePanel.tsx`)
- Slide-over drawer displaying 32 individual toggle switches with hover tooltips explaining capability functions.

### 2.6 1-Click Clearance Preset Selector (`PresetProfileSelector.tsx`)
- Quick-select profile pills (*Indie Film, Hollywood Blockbuster, Global Co-Production, GenAI-Assisted Production*) that instantly configure active feature toggle matrices.

---

## 📱 3. Responsive Layout & Accessibility Standards

- **Mobile & Tablet Optimization**: Fluid grid layout supporting 320px up to 4K ultra-wide studio displays.
- **WAI-ARIA Accessibility**: High-contrast text ratios (>= 7:1), keyboard navigation (`Tab` / `Enter`), and screen-reader accessible live regions for status updates.
