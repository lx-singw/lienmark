---
trigger: glob
globs: ["**/*.tsx", "**/*.jsx", "**/*.vue", "**/*.svelte", "**/components/**", "**/pages/**", "**/app/**"]
---

# UI & Accessibility Standards

- Prefer semantic HTML elements over `<div>`/`<span>` + bolted-on ARIA, wherever a
  semantic equivalent exists.
- All interactive elements are keyboard-navigable with a visible focus state.
- Meaningful images/icons get alt text or an accessible label; purely decorative
  assets are explicitly marked as such (`alt=""`, `aria-hidden`).
- Never use color alone to convey state (error/success) — pair with icon or text.
- Form inputs have associated labels; validation errors are announced to assistive
  tech, not just shown visually.
