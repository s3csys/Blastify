# Blastify Theme System

## Overview

The Blastify theme system allows users to customize the appearance of the application by selecting from predefined themes. The system includes:

1. Theme selection UI in the settings page
2. Quick theme switcher in the navbar
3. Theme persistence using localStorage
4. Server-side theme preference storage

## Available Themes

### Default
- Primary Color: #3B7DDD
- Font: Inter
- Layout: Sidebar
- Color Scheme: Light

### Data Able
- Primary Color: #4099ff
- Font: Poppins
- Layout: Sidebar
- Color Scheme: Light
- Style: Modern, flat design

### Teal Minimalist
- Primary Color: #00bcd4
- Font: Roboto
- Layout: Top navigation
- Color Scheme: Light
- Style: Minimal, subtle

### Dark Enterprise
- Primary Color: #7367f0
- Font: Inter
- Layout: Top navigation
- Color Scheme: Dark
- Style: Professional with gradients

## Implementation Details

### CSS Variables

The theme system uses CSS variables to define colors and other theme properties. These are defined in `static/css/theme-variables.css`.

### JavaScript

The theme switching functionality is implemented in `static/js/theme-switcher.js`, which handles:

- Theme persistence using localStorage
- Dynamic application of theme styles
- Loading theme-specific fonts
- Adding the theme switcher to the navbar

### Server-Side Integration

Theme preferences can be saved to the server via the `/settings/theme/update` endpoint in `app/routes/settings.py`.

## Adding New Themes

To add a new theme:

1. Add the theme configuration to the `THEMES` object in `theme-switcher.js`
2. Add the CSS variables for the theme in `theme-variables.css`
3. Add the theme option to the dropdown in `dashboard.html`
4. Add the theme card to the theme settings page in `settings/theme.html`