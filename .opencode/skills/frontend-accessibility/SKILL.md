---
name: frontend-accessibility
description: Apply practical accessibility checks to frontend markup and interactions, including keyboard use, semantics, focus, contrast, and motion.
---

# Frontend accessibility

- Prefer native semantic elements and controls. Associate form labels and instructions with their inputs; expose validation errors to assistive technology.
- Ensure every interactive control works by keyboard, has a visible focus indicator, and uses a descriptive accessible name.
- Preserve logical heading order and meaningful link/button text. Use ARIA only when native semantics are insufficient.
- Check text and control contrast, including hover, disabled, and error states; do not use color alone to convey meaning.
- Manage focus after dialogs, navigation, and dynamic updates. Announce important asynchronous status changes appropriately.
- Respect `prefers-reduced-motion`; avoid animation that blocks interaction or causes distracting movement.
- Keep touch targets usable on small screens and ensure zoom/reflow does not hide content or controls.

Validate the actual interaction path, not just the static markup.
