---
name: improve_ui
description: "Guidelines and design tokens to build premium, modern, and user-friendly web user interfaces for hackathon dashboards."
---

# Premium UI Design & Usability Guidelines

This skill provides styling principles, layout patterns, and CSS design tokens to build high-fidelity, visually stunning web interfaces.

## 1. Color Palette (Harmonious Dark Theme)
Avoid using default primary colors. Use curated, HSL-tailored scales for depth and modern aesthetics:
*   **Background (Deep Slate):** `hsl(222, 47%, 11%)`
*   **Card Background (Glass/Morphism):** `hsla(223, 47%, 16%, 0.6)` with `backdrop-filter: blur(12px)`
*   **Border / Divider:** `hsla(223, 47%, 25%, 0.4)`
*   **Primary Active (Electric Indigo):** `hsl(250, 89%, 65%)`
*   **Success (Teal-Green):** `hsl(162, 70%, 45%)`
*   **Warning (Amber-Gold):** `hsl(38, 92%, 55%)`
*   **Danger / Critical (Coral-Red):** `hsl(358, 85%, 60%)`
*   **Text Principal:** `hsl(210, 40%, 98%)`
*   **Text Secondary:** `hsl(215, 20%, 65%)`

## 2. Typography & Hierarchy
*   **Font Family:** Use clean, sans-serif fonts such as `Inter`, `Outfit`, or `Outfit` from Google Fonts.
*   **Hierarchy Scales:**
    *   `h1` (Main Objective): `2.25rem`, semi-bold, letter-spacing `-0.02em`.
    *   `h2` (Card Titles): `1.25rem`, medium, letter-spacing `-0.01em`.
    *   `p` (Body Copy): `0.95rem`, regular, line-height `1.5` for readability.
    *   `span` (Eyebrows/Tags): `0.75rem`, uppercase, bold, letter-spacing `0.05em`.

## 3. Spacing & Responsive Structure
*   **Grid Systems:** Use CSS Grid for the principal dashboard panels to ensure clear alignment.
    ```css
    .dashboard-grid {
      display: grid;
      grid-template-columns: 300px 1fr 400px;
      gap: 1.5rem;
      padding: 1.5rem;
    }
    ```
*   **Padding Density:** Maintain a minimum padding of `1.25rem` (`20px`) inside cards to give elements "room to breathe".
*   **Layout Alignment:** Ensure all labels and icons align to a standard baseline grid (4px / 8px blocks).

## 4. Interaction & Micro-Animations
An interface should feel alive. Add soft hover states and transitions to interactive items:
*   **Buttons & Links:**
    ```css
    .btn {
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px hsla(250, 89%, 65%, 0.35);
    }
    ```
*   **Cards:** Add a subtle glow border on hover.
    ```css
    .card {
      border: 1px solid var(--border-color);
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .card:hover {
      border-color: hsla(250, 89%, 65%, 0.5);
      box-shadow: 0 8px 30px hsla(0, 0%, 0%, 0.3);
    }
    ```

## 5. Polish Checklist
*   Ensure all buttons have matching active/disabled visual states.
*   Ensure scrollbars are styled and matching the dark theme.
*   Use custom SVG icons or emojis rather than empty list items.
*   Add a subtle pulsing dot animation on live-status badges.
