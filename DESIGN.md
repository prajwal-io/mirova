---
name: Mirova
description: An espresso research workspace with warm sunset light
colors:
  ground: "#181512"
  surface: "#211c19"
  raised: "#29221e"
  text: "#f5eadb"
  muted: "#b7a99b"
  border: "#3d322b"
  accent: "#f8b880"
  accent-dark: "#ffcf9b"
  soft: "#33271f"
  sunset-peach: "#ffd2a0"
  sunset-coral: "#f6ac89"
  sunset-lilac: "#d5b0dc"
  note-amber: "#edd09d"
  note-lilac: "#d5bee3"
  note-green: "#ccd8a8"
  note-rose: "#e6baa2"
typography:
  display:
    fontFamily: "Bricolage Grotesque, sans-serif"
    fontSize: "37px"
    fontWeight: 500
    lineHeight: "1.13"
    letterSpacing: "-1.3px"
  body:
    fontFamily: "Instrument Sans, Arial, sans-serif"
    fontSize: "14px"
  auth-accent:
    fontFamily: "Instrument Serif, Georgia, serif"
rounded:
  control: "8px"
  card: "11px"
  banner: "14px"
  dialog: "16px"
  note: "7px"
components:
  button-primary:
    textColor: "#342015"
    rounded: "{rounded.control}"
    height: "37px"
  button-secondary:
    backgroundColor: "#2d231c"
    textColor: "#e0c3a5"
    rounded: "{rounded.control}"
    height: "36px"
---

# Design System: Mirova

## Overview

**Creative North Star: Espresso at Sunset.** The user selected dark espresso with warm sunset glow and explicitly requested retro gradients and glows. Warm cream working text, expressive Bricolage headings, peach/amber light and lilac accents give the research workspace a relaxed, tactile character. Preserve the compact working layouts and evidence-first interactions.

## Colors

Espresso ground, layered brown surfaces and warm cream text establish the neutral structure. The peach-to-coral-to-lilac sunset gradient distinguishes primary controls and signature artwork. Amber, lilac, green and rose notes distinguish editable roadmap phases. Values in the frontmatter are extracted from `app/retro.css`, which is imported after `globals.css` and owns the final theme.

## Typography

Bricolage Grotesque carries brand, page headings and reflective display moments; Instrument Sans carries navigation, source content, labels and controls. Instrument Serif provides the auth accent. The workspace greeting is 500 37px/1.13 with -1.3px tracking; mobile uses 29px with -.8px tracking; wide screens use 42px. Banner headings use 35px, copilot welcome headings 27px, and working labels generally 11?13px. Miniature board art is illustrative and is not a working text scale.

## Layout

Research tool responsiveness follows `app/features.css`: at 1200px, narrow the insight panel to 280px and history rail to 190px; at 1000px, stack map/insights and history/conversation, cap history at 180px, and stack task fields. At 740px, stack the team columns, use 20px team-panel padding, allow sync details to wrap, and restore paired task fields within the full-width panel. Preserve intrinsic wrapping and flexible minimum widths for names, evidence, and discussion text.

The workspace retains its existing sidebar, central canvas and right copilot composition. At 1500px and above the sidebar is 246px and the copilot 340px; compact desktop reduces these to 200px and 280px. At 1010px and below the overview copilot hides while full copilot access remains available. At 740px and below the 240px sidebar becomes a sheet, the canvas loses its sidebar margin, stats become two columns and board cards become a single-column list. Editable roadmap phases retain two columns. Desktop topbar height is 72px, mobile workspace topbar 60px. Banners use 223px minimum height, 245px on wide screens and 220px on mobile. The copilot minimum height is 775px.

The mobile sign-in composition uses a single-column grid with 23px side padding and 22px gap. Its heading and supporting text precede the form; the form is order 3 and the 230px decorative scene order 4. The auth form side is at most 460px wide; mobile form-card padding is 24px 23px, inputs are 49px tall and submit has a 47px minimum height. Auth mobile topbar is 80px. Preserve the form before the decorative scene. Source inspection is a screen-bounded 480px right drawer; import dialogs are 520px wide with 32px padding, reduced to 26px 22px on mobile. Existing CSS remains authoritative for exact responsive dimensions.

## Elevation & Depth

Dark tonal layering and thin warm borders provide structure. Subtle ambient sunset glows are intentional user requirements: primary controls use `0 8px 32px #f3a07326`; hover strengthens the light to `0 8px 35px #e9a67542` and lifts by 1px. Composer focus combines a warm border and shallow halo. Dialogs use a dark scrim, 7px backdrop blur and deeper structural shadow. Keep ordinary research content legible within this atmosphere.

## Shapes

Controls use 8px corners, board cards 11px, banners 14px, dialogs 16px and roadmap notes 7px. Cards and working panels have thin brown edges. Rounded art, light pools and gradient marks belong to signature illustrations and controls.

## Components

Primary actions use the 115-degree sunset gradient, dark espresso text, 600 weight, warm glow and visible keyboard outline. Hover lifts 1px; active returns to rest; disabled removes glow and movement. Secondary controls use dark brown fill and a warm border. Selected navigation has a brown gradient and inset warm edge. Inputs use dark fill, warm text and peach caret; focus-visible uses a 2px peach outline with 4px offset. Composer and search focus-within add a restrained warm halo.

Board cards lift 3px and warm their border on hover. Roadmap notes retain readable dark ink on amber, lilac, green and rose fills. Citations, source inspection, editable plans and explicit approval remain functional components, not artwork. Sign-in shares the sunset action grammar with a serif accent and decorative scene.

Reduced-motion preferences disable animations, transitions and smooth scrolling through the existing global override. Preserve that override in future effects and component variants.

### Research and collaboration tools

These tools extend the approved espresso and sunset system in `components/WorkspaceTools.tsx` and `app/features.css`. Preserve the existing brand, font families, primary actions, and palette when adding research or team controls.

- **Saved chat history:** use a 220px rail beside a flexible conversation, with 18px spacing. The rail uses a 12px radius, espresso `#211b17`, and the existing border token. History titles clamp to two lines; dates remain secondary. Selected rows use `#4a3020` with `#ffd0a0` text, and hover uses `#38281d`.
- **Insights and theme selection:** place a 310px insight panel beside the map. Use a 12px radius, 19px padding, and `#261d18`. Full-width theme buttons use an 8px radius and show the theme summary and source count. Selection uses `#4a3120`, `#af7c4b` border, and `#ffdbac` text. Group gaps and conflicts beneath thin brown dividers; keep linked evidence available as compact source buttons.
- **Sync controls:** status copy and manual refresh remain compact and wrap with available width. Settings use a 12px radius and warm `#302318` surface. The 39 by 23px switch has a 15px circular thumb, 200ms background/position transitions, and a visible `#ffd1a0` keyboard outline. Checked state uses `#e7b47f` with a dark thumb. Keep cadence and last-sync details subordinate to the setting label.
- **Team studio:** compose equal flexible columns with a 24px gap. Group workspace selection, membership, invites, and joining in one panel, with discussion beneath; place task creation and task rows alongside. Panels use `#261d17`, a `#59402b` border, 12px radius, and 23px padding. Member rows use 32px initial avatars and quiet Owner/Editor labels. Invite codes wrap within their container.
- **Task forms and discussions:** use visible field labels, 41px-high inputs, 7px radii, `#1e1712` backgrounds, `#825a36` borders, and `#f2cba0` input text. Pair task owner and deadline fields when space allows. Discussion textareas use an 8px radius and at least 80px height; preserve line breaks and wrap long content. Separate messages and task rows with tonal rules. Show author/date or owner/deadline as secondary metadata. Completed task titles use a strike-through and muted text.
- **Roadmap ownership:** keep compact owner and date fields inside the existing light roadmap notes. Use the note's warm ink and translucent light input treatment, retaining the native date control. Preserve readable metadata beneath the step content.

## Do's and Don'ts

- **Do** use espresso surfaces, warm cream text, Bricolage headings and Instrument Sans working text.
- **Do** retain the user-requested peach/amber/lilac gradients and subtle sunset glows.
- **Do** preserve visible focus and reduced-motion behavior.
- **Do** place the mobile sign-in form before decorative artwork.
- **Don't** restore the previous warm-light/sage baseline.
- **Don't** promote miniature board artwork into a usable typography scale.
- **Don't** replace existing research layouts with decorative specimens.
