# Design QA

final result: passed

## Scope and reference

This is a new management surface using the existing Amazon Ads workbench's code
design language, not a pixel-identical recreation of a supplied image. The source
reference was the existing light palette, blue navigation, rounded panels and
compact tables. Feature-specific content and layouts are intentional extensions.

## Rendered evidence

Real Chromium browser against the deployed app, desktop 1440x1000 and mobile
390x844. Screenshots are retained in a private local acceptance directory,
outside the repository, and are intentionally not published.

- mcp-token-desktop.png: deployed administrator workspace, Token page.
- mcp-token-mobile.png: same page and actual account at mobile width.
- report-preview-fixture.png: persisted preview, explicitly labeled test data.
- logs-fixture.png: audited task/approval transitions for the temporary QA user.

## Checks

| Surface | Result |
| --- | --- |
| Typography | Chinese headings, labels, IDs and monospace fields readable at both viewports |
| Layout | Desktop panels aligned; mobile heading/action wrapping fixed; tables scroll internally |
| Colors/tokens | Existing light/blue language retained; distinct pending, success and failure states |
| Assets | Phosphor icons; no missing raster assets or invented product imagery |
| Copy | Empty reports distinguished from pending tasks; queued plans are not described as executed |
| Navigation | All seven routes reachable; current mobile navigation scrolls into view |
| Keyboard/modal | Escape close and focus containment implemented; confirmation disabled until exact text |
| Token flow | Create, show-once, hide and revoke tested against PostgreSQL; test tokens cleaned |
| Report flow | Queue, persisted completion, row preview and downloaded JSON content checked |
| Approval flow | Typed confirmation queues a bound plan; worker dispatcher tested with fake upstream only |
| Console | Final authenticated page has zero errors/warnings; catalog 500 fixed and regression-tested |

## Issues resolved

- Capability catalog failed to serialize Click UNSET defaults; fixed and verified through UI and real MCP HTTP.
- Mobile logout was hidden; it is now visible.
- Mobile title/action crowding and breadcrumb wrapping were corrected.
- Session logout clears cached data before another user can enter the workspace.

No unresolved P0/P1/P2 findings in the checked flows. Remaining limitations:
this is not a full WCAG or cross-browser certification; production ad writes were
not tested during deployment; raw API parameter descriptions retain English where
they come from the existing CLI contract.
