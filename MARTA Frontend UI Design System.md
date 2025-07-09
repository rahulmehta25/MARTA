# MARTA Frontend UI Design System

## Design Principles

### Inspired by Uber's Design Philosophy
- **Go big**: Prioritize larger font sizes for legibility and accessibility
- **Less is more**: Optimize for fewer style options to avoid decision paralysis
- **Simple semantics**: Provide guidance without being overly prescriptive
- **Map-first approach**: The map is the primary interface element

### Map UI Best Practices
- **Match brand identity**: Colors, fonts, and overall vibes should feel cohesive
- **Reduce cognitive load**: Remove unnecessary labels, icons, and roads that don't matter to the user's goal
- **Prioritize visual hierarchy**: Important points (destinations, routes, regions) should stand out, while secondary details stay subtle
- **Clear visual indicators**: Users should always know which layers are active and what state the interface is in

## Color Palette

### Primary Colors
- **Black**: #000000 (Primary text, buttons, high contrast elements)
- **White**: #FFFFFF (Backgrounds, cards, contrast)
- **Gray Scale**: 
  - Light Gray: #F5F5F5 (Background surfaces)
  - Medium Gray: #9E9E9E (Secondary text, borders)
  - Dark Gray: #424242 (Secondary elements)

### Accent Colors
- **Green**: #00C853 (Success states, available/active routes)
- **Red**: #FF1744 (Error states, overloaded routes)
- **Blue**: #2196F3 (Information, selected states)
- **Orange**: #FF9800 (Warning states, moderate demand)

### Map-Specific Colors
- **Demand Heatmap**:
  - Low Demand: #4CAF50 (Green)
  - Medium Demand: #FF9800 (Orange)
  - High Demand: #F44336 (Red)
  - Overloaded: #9C27B0 (Purple)

## Typography

### Font Family
- **Primary**: Inter (fallback for Uber Move)
- **Monospace**: JetBrains Mono (for data/numbers)

### Type Scale
- **Display Large**: 48px / 56px line height
- **Display Medium**: 36px / 44px line height
- **Heading Large**: 24px / 32px line height
- **Heading Medium**: 20px / 28px line height
- **Body Large**: 16px / 24px line height
- **Body Medium**: 14px / 20px line height
- **Body Small**: 12px / 16px line height

### Font Weights
- **Regular**: 400
- **Medium**: 500
- **Semibold**: 600
- **Bold**: 700

## Layout & Spacing

### Grid System
- **Base unit**: 4px
- **Common spacing**: 8px, 12px, 16px, 24px, 32px, 48px, 64px
- **Container max-width**: 1200px
- **Breakpoints**:
  - Mobile: 320px - 768px
  - Tablet: 768px - 1024px
  - Desktop: 1024px+

### Component Spacing
- **Card padding**: 16px - 24px
- **Button padding**: 12px 24px
- **Input padding**: 12px 16px
- **Section margins**: 32px - 48px

## Component Architecture

### Core Components
1. **Map Container**: Full-screen map with overlay elements
2. **Search Bar**: Top-positioned with autocomplete
3. **Bottom Drawer**: Expandable panel for details
4. **Floating Action Buttons**: Primary actions overlay
5. **Layer Controls**: Map layer toggles
6. **Info Cards**: Contextual information display

### Layout Structure
```
┌─────────────────────────────────────┐
│           Search Bar                │
├─────────────────────────────────────┤
│                                     │
│                                     │
│            Map View                 │
│                                     │
│                                     │
│  [FAB] [FAB]                       │
├─────────────────────────────────────┤
│         Bottom Drawer               │
└─────────────────────────────────────┘
```

## Interaction Patterns

### Map Interactions
- **Pan**: Drag to move around
- **Zoom**: Pinch/scroll to zoom in/out
- **Tap**: Select stops, routes, or points of interest
- **Long press**: Context menu or detailed info

### Navigation Patterns
- **Search-first**: Primary entry point for destination selection
- **Progressive disclosure**: Show more details as user drags up bottom drawer
- **Contextual actions**: Floating buttons for primary actions
- **Layer management**: Toggle different data visualizations

## Accessibility

### Color Contrast
- **Text on white**: Minimum 4.5:1 ratio
- **Text on colored backgrounds**: Minimum 3:1 ratio
- **Interactive elements**: Clear focus states

### Touch Targets
- **Minimum size**: 44px x 44px
- **Spacing**: 8px minimum between targets
- **Feedback**: Visual and haptic feedback for interactions

### Screen Reader Support
- **Semantic HTML**: Proper heading hierarchy
- **ARIA labels**: Descriptive labels for map elements
- **Alternative text**: Descriptions for visual information

## Animation & Motion

### Transition Timing
- **Fast**: 150ms (hover states, small changes)
- **Medium**: 300ms (panel slides, route animations)
- **Slow**: 500ms (major state changes)

### Easing Functions
- **Standard**: cubic-bezier(0.4, 0.0, 0.2, 1)
- **Decelerate**: cubic-bezier(0.0, 0.0, 0.2, 1)
- **Accelerate**: cubic-bezier(0.4, 0.0, 1, 1)

### Animation Principles
- **Purposeful**: Animations should guide user attention
- **Responsive**: Quick feedback for user actions
- **Smooth**: 60fps performance target
- **Reduced motion**: Respect user preferences

## Data Visualization

### Heatmaps
- **Opacity**: 0.6 - 0.8 for overlay visibility
- **Radius**: Adaptive based on zoom level
- **Color progression**: Smooth gradients between states

### Route Lines
- **Width**: 3-6px based on importance
- **Style**: Solid for active, dashed for proposed
- **Animation**: Flow direction indicators

### Markers & Icons
- **Size**: 24px - 32px for primary markers
- **Style**: Filled for active, outlined for inactive
- **Clustering**: Group nearby markers at lower zoom levels

This design system provides the foundation for creating a cohesive, accessible, and user-friendly MARTA frontend interface inspired by Uber's design principles while optimized for transit data visualization.

