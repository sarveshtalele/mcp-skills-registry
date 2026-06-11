# Figma mapping

Map each legacy screen to a Figma frame, then to a React component:
- Frame name → component name (PascalCase, suffixed `Page`/`View`/`Screen`).
- Export design tokens (color/spacing/typography) into the app's theme.
- Keep one component per file under `components/<Name>.tsx`.
