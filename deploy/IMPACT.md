# Local Docker Impact Review

The user approved deployment on 2026-10-14. The three containers below are running
locally. The 11 pre-existing containers retained their IDs and running states.
Human approval remains required for a new deployment in another environment.

| Resource | Proposed change | Effect on existing services |
| --- | --- | --- |
| ads-mcp-6666-api | New linux/amd64 container; loopback 6666 and browser-safe 16666 | No reuse of existing service ports; max 512 MiB / 1 CPU |
| ads-mcp-6666-worker | New linux/amd64 background worker, no published port | Separate process, max 512 MiB / 1 CPU |
| ads-mcp-6666-postgres | New PostgreSQL 16 container; no published port | Does not use host PostgreSQL or any existing database; max 768 MiB / 1 CPU |
| ads-mcp-6666-pgdata | New named volume | No existing volume mounted, copied or modified |
| ads-mcp-6666-net | New bridge network | No existing network modified |

The new services share Docker Desktop CPU/RAM with existing services, so resource
usage is not literally zero. They are bounded to 1.75 GiB RAM and 3 CPUs in total.
No restart, deletion, pruning, migration, or configuration change of an existing
container is part of this deployment. Recheck port and resource names immediately
before creating containers. PostgreSQL's internal 5432 is not a host-port binding.

6666 is a Chromium restricted port. The browser uses 16666; API/MCP callers can
still use 6666. Both port mappings address the same authenticated service.
