# Screenshots

Every screen and state of the web app at 390 px wide (a phone), in English (`en-*`) and Hindi
(`hi-*`), taken by `web/e2e/screens.spec.js`:

```powershell
cd web; npm run build; npx playwright test screens --project=phone
```

They are taken with `GNANI_MOCK=1` (src/gnani_mock.py): what the speech service "heard", and
every candidate, comes from made-up Prisma answers, not real recognition. The accounts, names
and emails are test data. The background is frozen (reduced motion) so the pictures are stable.
