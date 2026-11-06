# Screenshots

Every screen and state of the web app, in English (`en-*`) and Hindi (`hi-*`), in the light and
dark themes, at 390 px wide (a phone) and 1440 px wide (a desktop): 31 states × 8 = 248 pictures,
taken by `web/e2e/screens.spec.js`:

```powershell
cd web; npm run build; npx playwright test screens
```

| Folder | Width | Theme |
|---|---|---|
| `390-light/` | 390 (the phone project) | light |
| `390-dark/` | 390 | dark |
| `1440-light/` | 1440 (the desktop project) | light |
| `1440-dark/` | 1440 | dark |

The theme is left on automatic and follows the emulated device, as it does by default. Tall
pages are shot at their full height with the window that tall, so the tab bar sits where it
really is; a screen with a sheet open is shot as the screen shows it.

They are taken with `GNANI_MOCK=1` (src/gnani_mock.py): what the speech service "heard", and
every candidate, comes from made-up Prisma answers, not real recognition. The accounts, names
and emails are test data. Motion is reduced, so the pictures are stable (that is also why the
red ring behind the record button is still in `*-16-speak-recording`).
