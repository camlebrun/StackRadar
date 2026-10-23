## ADDED Requirements

### Requirement: Portfolio design tokens
Every page SHALL define its colours, fonts and radii as CSS custom properties on `:root`, using the portfolio values: page background `#f5f0e8`, primary `#8d4f26` (hover `#74401f`), heading `#1b2230`, body text `#4f5d73`, muted text `#78808e`, accent `#6b8e74`, card border `#e6d8c8`, card radius `1rem`. Headings SHALL use Playfair Display and body text DM Sans, with system serif and sans-serif fallbacks.

#### Scenario: Tokens drive the look
- **WHEN** any page is loaded
- **THEN** its background computes to `#f5f0e8` and no rule outside `:root` hard-codes a colour used by these tokens

#### Scenario: Fonts fail to load
- **WHEN** the Google Fonts request fails
- **THEN** text renders with the fallback fonts and layout stays usable

### Requirement: Cards and buttons
Release cards SHALL be white with a 1px `#e6d8c8` border and `1rem` radius. Buttons and filter chips SHALL be pill-shaped (radius 999px); the primary button SHALL be brown on white text and the secondary SHALL be transparent with a `#dccfbe` border.

#### Scenario: Chip appearance
- **WHEN** a filter chip is rendered active
- **THEN** it is a pill with the primary brown background and white text

### Requirement: Severity palette is readable on beige
Severity badges (`critical`, `high`, `medium`, `low`, `none`) SHALL use a warm palette and every badge's text SHALL reach a contrast ratio of at least 4.5:1 against its own badge background.

#### Scenario: Contrast check
- **WHEN** the five badge colour pairs are measured
- **THEN** each ratio is at least 4.5:1

### Requirement: No dark theme
The pages SHALL NOT switch palette with `prefers-color-scheme`.

#### Scenario: Dark OS setting
- **WHEN** the visitor's system prefers a dark colour scheme
- **THEN** the page renders the same light palette
