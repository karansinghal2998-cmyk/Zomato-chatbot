---
name: Culinary Intelligence Portal
colors:
  surface: '#1e0f0f'
  surface-dim: '#1e0f0f'
  surface-bright: '#473534'
  surface-container-lowest: '#180a0a'
  surface-container-low: '#271717'
  surface-container: '#2c1b1b'
  surface-container-high: '#372625'
  surface-container-highest: '#423030'
  on-surface: '#f9dcda'
  on-surface-variant: '#e4bebc'
  inverse-surface: '#f9dcda'
  inverse-on-surface: '#3e2c2b'
  outline: '#ab8987'
  outline-variant: '#5b403f'
  surface-tint: '#ffb3b1'
  primary: '#ffb3b1'
  on-primary: '#680011'
  primary-container: '#ff535a'
  on-primary-container: '#5b000e'
  inverse-primary: '#bb162c'
  secondary: '#ffb3b3'
  on-secondary: '#680015'
  secondary-container: '#a30227'
  on-secondary-container: '#ffadad'
  tertiary: '#71d7cf'
  on-tertiary: '#003734'
  tertiary-container: '#32a099'
  on-tertiary-container: '#00302d'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#ffdad9'
  secondary-fixed-dim: '#ffb3b3'
  on-secondary-fixed: '#400009'
  on-secondary-fixed-variant: '#920021'
  tertiary-fixed: '#8ef4eb'
  tertiary-fixed-dim: '#71d7cf'
  on-tertiary-fixed: '#00201e'
  on-tertiary-fixed-variant: '#00504c'
  background: '#1e0f0f'
  on-background: '#f9dcda'
  surface-variant: '#423030'
typography:
  display-xl:
    fontFamily: Outfit
    fontSize: 64px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 40px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
  title-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-max: 1440px
  gutter: 24px
  margin-desktop: 40px
  panel-padding: 24px
---

## Brand & Style

This design system targets a high-tech, data-driven food exploration experience for power users. The aesthetic merges **Glassmorphism** with a **Corporate Modern** structure, creating a "Mission Control" atmosphere for gastronomy. 

The interface leverages deep slate tones to provide a premium, cinematic backdrop that allows vibrant food photography and data visualizations to pop. By utilizing translucent layers and background blurs, the UI achieves a sense of physical depth and sophisticated hierarchy, moving away from flat design into a more tactile, digital environment. 

The emotional response should be one of precision, appetite, and technological empowerment.

## Colors

The palette is anchored in **Deep Slate Navy** to maintain a high-end dark mode aesthetic. **Zomato Red** serves as the primary action color, while **Crimson Glow** is reserved for hover states and high-energy accents.

- **Primary Actions:** Use `#E23744`.
- **Success/Ratings:** Use `#10B981` to denote positive sentiment and high quality.
- **Attention/Badges:** Use `#F59E0B` for specialty callouts and awards.
- **Glass Layers:** Use `rgba(30, 41, 59, 0.75)` for all elevated panels to maintain legibility against the darker `#0F172A` foundation.

## Typography

This design system uses a dual-type approach. **Outfit** provides a geometric, modern feel for high-level headings and brand moments. **Inter** is used for all functional UI elements, data tables, and body copy to ensure maximum legibility at various scales.

Headlines should utilize tighter letter-spacing to reinforce the "high-tech" look. Labels should be uppercase when used in navigation or as section headers to create a clear structural hierarchy.

## Layout & Spacing

The layout follows a **Fixed Grid** model on desktop, centered within a 1440px container. 

- **Grid:** 12-column system with 24px gutters.
- **Sidebar:** A fixed 280px glass sidebar for primary navigation.
- **Panels:** Data sets and restaurant lists should be housed in distinct translucent panels.
- **Rhythm:** Use multiples of 8px (8, 16, 24, 32, 48, 64) for all padding and margins to maintain mathematical consistency.

## Elevation & Depth

Hierarchy is established through **Glassmorphism** and subtle border treatments rather than traditional heavy shadows.

- **Level 0 (Base):** Deep Slate Navy `#0F172A`.
- **Level 1 (Panels):** `rgba(30, 41, 59, 0.75)` with a `backdrop-filter: blur(16px)`.
- **Level 2 (Modals/Popovers):** `rgba(45, 55, 72, 0.9)` with a `backdrop-filter: blur(24px)`.
- **Accents:** All panels must have a 1px solid border at `rgba(255, 255, 255, 0.1)` on the top and left edges to simulate a "light catch" on the glass edge.

## Shapes

The shape language is **Rounded**, striking a balance between the organic nature of food and the precision of a data portal. 

- **Standard Elements:** 0.5rem (8px) radius for buttons and input fields.
- **Cards/Panels:** 1rem (16px) radius for large layout containers.
- **Search Bars:** Should utilize the `rounded-xl` (1.5rem / 24px) setting to stand out as a primary interaction point.

## Components

### Buttons
- **Primary:** Solid `#E23744` with white text. Subtle inner glow on hover using `#FF5260`.
- **Secondary:** Translucent white `rgba(255,255,255,0.1)` with a 1px border and blur.

### Input Fields
- Dark backgrounds `rgba(15, 23, 42, 0.5)` with `Inter` typography. 
- Focus state: 1px solid `#FF5260` with a subtle outer glow.

### Cards (Restaurant/Data)
- Glass panels with 16px padding.
- Imagery should have a slight vignette to ensure white text overlays remain readable.
- Ratings should be displayed in a high-contrast `#10B981` pill.

### Data Visualizations
- Charts should use the primary Red, Emerald Green, and Amber palette against the navy background. 
- Grid lines in charts should be kept at low opacity `rgba(255,255,255,0.05)`.

### Chips & Badges
- Small, uppercase labels with 4px border radius.
- Backgrounds should be low-opacity versions of the accent colors (e.g., Emerald at 15% opacity for positive labels).