# PubChat release checklist

Before assigning or promoting a version:

- review merged changes and open P0/P1 blockers;
- confirm `VERSION` follows `docs/versioning.md`;
- update `CHANGELOG.md`;
- backend contract tests pass and `app.version` equals `VERSION`;
- frontend production build receives the same version;
- Alembic has one head and migrations are reviewed;
- security regression guards pass;
- release head CI is green;
- alpha → beta or beta → stable promotion satisfies the readiness gate, not just a date or commit count.
