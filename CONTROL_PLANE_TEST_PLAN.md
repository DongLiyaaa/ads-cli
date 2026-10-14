# MCP Control Plane Verification

No test may mutate a real advertising account. Existing containers and databases
must remain untouched. Starting the isolated Compose project requires the user's
review of the exact container/port/volume impact list.

## Unit and contract coverage

- Existing CLI core/E2E tests remain compatible.
- Context-local credentials and outputs cannot leak across threads or users.
- All exposed command contracts produce valid schemas; file-path commands are excluded.
- Server plans cannot execute advertisements; approved execution uses the shared dispatcher.
- Password/token hashing, encryption, redaction, URL/path restrictions and payload binding.
- Report date validation, task state transitions, incomplete/mixed API responses.
- Browser frontend build, empty/error states and responsive layout.

## PostgreSQL integration (isolated container only)

- Bootstrap/login/session/CSRF; anonymous requests and MCP tokens cannot approve writes.
- Account/token/task/log ownership and account-scoped token grants.
- Token create/show-once/revoke/expiry and real MCP initialize/list/call handshake.
- Fake upstream report PENDING -> COMPLETED -> persisted rows, survives worker restart.
- Expired report URLs are refreshed and raw URL/secret values never enter logs.
- Duplicate idempotency keys, row locking, concurrent approval and five-slot API limit.
- Partial mutation response and interrupted mutation become PARTIAL/UNKNOWN, not success/retry.
- Browser account, task, approval, token and audit flows against this isolated DB.

## Live acceptance

Only read-only Amazon calls may be used without a separate concrete write approval.
Record exact test commands and results in the delivery report; do not describe
unrun Docker or PostgreSQL acceptance as passed.
