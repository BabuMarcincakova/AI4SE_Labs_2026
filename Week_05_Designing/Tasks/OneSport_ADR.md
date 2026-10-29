# ADR-001: Select a modular monolith with PostgreSQL for OneSport

- **Status:** Accepted
- **Date:** 2026-10-29
- **Decision owners:** OneSport engineering team
- **Scope:** Initial production architecture
- **Related record:** [Task 1 architecture review](./OneSport_architecture_review_Task1.md)

## Executive summary

| Option | Operational complexity | Transactional consistency & concurrency | Infrastructure & cost at tens of thousands of users | Time-to-market / development velocity | Assessment |
|---|---|---|---|---|---|
| 1. Modular monolith | **Low to moderate**: one deployable system, one primary database, separate bounded workers | **Strongest and simplest** for cross-feature transactions; PostgreSQL constraints and pair locks handle social/collection races | **Predictable and moderate**: one database plus scalable API/worker pools; read replicas and caching available | **Fastest initial delivery**: simple local setup, migrations, tests, and debugging | **Selected initial architecture** |
| 2. Event-driven microservices | **High**: many deployments, databases, broker, tracing, retries, and operational runbooks | Strong inside each service but **eventual across services**; sagas, outbox/inbox, and reconciliation required | **Highest baseline cost**: multiple runtimes and databases; independent scaling can pay off only for genuinely hot domains | **Slowest initial delivery**: distributed contracts, deployment automation, and failure testing required | Defer until independent scaling or team autonomy justifies it |
| 3. Serverless managed state | **Moderate to high**: less server operations but substantial cloud/IAM/workflow/observability complexity | Strong database transactions, but **bounded by one write database**; retries and lock contention require admission control | **Potentially efficient for bursty workloads**, but database, invocation, queue, workflow, and egress costs can be unpredictable | **Fast for simple handlers**, slower for robust workflows, realtime delivery, local testing, and provider integration | Consider selectively for bursty workloads |

## Context

OneSport provides:

- Account signup, login, logout, profile changes, credential changes, and
  GDPR-compliant account deletion
- Admin-managed sports news and sporting-event ticket offers
- Recent-news and upcoming-ticket browsing with country filtering
- Saved news and saved tickets, including add, remove, view, and clear-all
- User lookup by email
- Friend requests, acceptance/refusal, friendship listing, and removal
- Availability checks when ticket offers are viewed
- Availability checks for saved tickets at login and continuously afterward,
  with near-real-time user notification when an offer becomes unavailable

The system is expected to serve tens of thousands of users. OneSport displays
and saves ticket offers; it does not sell tickets, process payments, own
inventory, or issue tickets. News and event data are maintained by an admin
group rather than imported from external providers.

The requirements favor transactional operations around users, collections,
friendships, and account deletion. They do not currently establish a need for
independently deployable services, extreme write throughput, multiple
autonomous teams, or provider-independent cloud portability.

## Decision drivers

1. Preserve correctness for user-owned data and social relationships.
2. Provide safe concurrent friend-request and friendship operations.
3. Support GDPR account deletion without deleting shared catalog data.
4. Detect ticket availability and notify users reliably.
5. Support tens of thousands of users without premature operational overhead.
6. Make module ownership enforceable rather than merely documented.
7. Keep local development, testing, migrations, and incident response
   tractable.
8. Retain an incremental path to read scaling, worker scaling, and later
   domain extraction.
9. Avoid making a broker, service mesh, workflow platform, or cloud provider
   mandatory before product needs justify it.

## Considered options

### Option 1: Modular monolith with PostgreSQL

One deployable API contains strict Identity, Catalog, Collections, Social,
Notifications, and Admin modules. A separate availability/notification worker
uses the same domain code and database boundaries. PostgreSQL is the
transactional source of truth.

Strengths:

- Local transactions and foreign keys
- Straightforward friend-request locking
- Simple account-deletion coordination
- Lower operational cost and easier end-to-end testing
- Clear path to read replicas, caches, worker scaling, and later extraction

Weaknesses:

- Requires discipline to prevent cross-module persistence access
- A shared database remains a common failure and capacity boundary
- Independent deployment and scaling are limited

### Option 2: Event-driven microservices

Identity, Catalog, Collections, Social, Availability, Notifications, and
Audit are independently deployable services. Each owns a database and
communicates through synchronous APIs and a durable event broker.

Strengths:

- Strong service ownership boundaries
- Independent deployment and scaling
- Natural event flow for availability changes and notifications
- Better fit for multiple autonomous teams

Weaknesses:

- Eventual consistency and distributed tracing
- Transactional outbox, inbox, replay, and schema evolution requirements
- GDPR deletion becomes a deadline-driven multi-database workflow
- Higher deployment, testing, and operational complexity

### Option 3: Serverless application with managed state

API gateway and short-lived stateless functions use managed PostgreSQL,
queues, event topics, cache, object storage, and a durable workflow engine.

Strengths:

- Reduced server fleet operations
- Automatic scaling for bursty workloads
- Managed retry, scheduling, and workflow primitives
- Per-function permissions and pay-per-use potential

Weaknesses:

- Function concurrency can overwhelm the relational database
- Retry storms can amplify connection and lock pressure
- Cold starts, vendor coupling, and production/local differences
- Real-time sockets and GDPR deletion still require durable external state
- Observability and cost control are non-trivial

## Decision

Select **Option 1: a modular monolith with PostgreSQL** for the initial
OneSport production system.

The application is one deployable unit, but it is not an unstructured
monolith. Modules own their domain behavior and persistence adapters. They
communicate through typed application services, commands, and selected domain
events. Direct cross-module persistence access is prohibited.

Use a separate worker deployment for availability monitoring and notification
processing. This isolates long-running or bursty work without introducing
distributed ownership of the core transactional model.

### Selected system layout

```text
                         +----------------------+
                         | Web / mobile clients |
                         +----------+-----------+
                                    |
                         HTTPS REST / BFF API
                                    |
                     +--------------v---------------+
                     | Modular OneSport application |
                     |-------------------------------|
                     | Identity & Profile            |
                     | Catalog & Admin               |
                     | Collections                  |
                     | Social Graph                  |
                     | Notifications                |
                     +------+------------------------+
                            |
                 Typed module APIs / domain events
                            |
          +-----------------v------------------+
          | PostgreSQL transactional source   |
          | identity | catalog | collections   |
          | social | notifications | audit     |
          +-----------------+------------------+
                            ^
                            |
              Separate bounded worker pools
          +----------------+----------------+
          |                                 |
 +--------+---------+             +---------+--------+
 | Availability     |             | Notification     |
 | monitor worker  |             | delivery worker  |
 +--------+---------+             +---------+--------+
          |                                 |
          +------ durable jobs/events ------+
                            |
                 Realtime connection service
                 WebSocket / SSE gateway
```

The realtime connection service may be managed infrastructure or a separately
scaled component. Domain modules do not track socket node addresses.

## Architecture details

### Module and database boundaries

Use owned PostgreSQL schemas:

```text
identity
catalog
collections
social
notifications
audit
```

Each module owns its tables and persistence adapters. Runtime database roles
should receive only the access required by the module. Cross-module reads use
narrow read views or typed application services rather than arbitrary joins.

Enforcement mechanisms:

- Separate schemas and table ownership
- Least-privilege runtime and migration roles
- Private persistence packages per module
- Architectural dependency tests rejecting forbidden imports
- CI checks for forbidden cross-schema references and migration access
- Explicit review for cross-module views

These controls do not make a shared database physically independent. They make
ownership explicit and cause many accidental violations to fail early.

### Core relational constraints

Important constraints include:

```sql
CREATE TABLE social.friendships (
    user_low_id  bigint NOT NULL,
    user_high_id bigint NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_low_id, user_high_id),
    CHECK (user_low_id < user_high_id)
);

CREATE UNIQUE INDEX one_pending_request_per_direction
ON social.friend_requests(sender_id, recipient_id)
WHERE status = 'pending';

CREATE UNIQUE INDEX one_saved_ticket_per_user
ON collections.saved_tickets(user_id, ticket_id);
```

Foreign keys, `NOT NULL` constraints, status checks, and indexes should be
added according to the final schema. Shared catalog records must not cascade
from user deletion.

### Concurrent friend-request handling

Use PostgreSQL `READ COMMITTED` for normal operations, a short transaction,
and deterministic pair locking:

1. Compute `user_low_id = min(user_a, user_b)` and
   `user_high_id = max(user_a, user_b)`.
2. Lock both user rows in ascending ID order using `SELECT ... FOR UPDATE`.
3. Re-read friendship and pending-request state after locks are acquired.
4. Apply the reciprocal-request policy.
5. Transition the request and insert the canonical friendship atomically.
6. Commit and return an idempotent result.

Ascending lock order prevents the usual A-then-B/B-then-A deadlock. The
friendship primary key is a final duplicate guard. Opposite-direction
requests are consolidated into one pending relationship rather than
automatically creating a friendship merely because both users clicked send.

### Ticket availability and notifications

Catalog is authoritative for ticket-offer state. The user-facing catalogue
query returns availability and `last_checked_at`. The availability worker:

- Processes bounded batches
- Uses a `next_check_at` index
- Has a separate connection pool and database role
- Uses short transactions
- Represents source failures as `unknown`, not `unavailable`
- Emits one transition event when availability changes

Notifications are persisted before live delivery. A user can have multiple
active connections; a realtime gateway maintains presence records and routes
messages through a broker or managed connection service. Domain code never
depends on a particular socket node.

On reconnect, the client supplies a cursor or last-seen event ID and receives
missed notifications from durable storage.

### Transactional outbox and worker isolation

For module-originated events:

1. Update module state.
2. Insert an outbox event in the same PostgreSQL transaction.
3. A relay claims pending rows with a lease.
4. Publish using a stable event ID.
5. Mark published only after broker acknowledgement.
6. Retry expired leases with exponential backoff.

Use `pending`, `publishing`, `published`, and `dead_letter` states with attempt
counts, next-attempt times, leases, and last errors. Duplicate publication is
expected; consumers must be idempotent.

Web and worker workloads use separate bounded connection pools. Background
workers use bounded batches, queue backpressure, statement/transaction
timeouts, and reserved capacity. Bulk admin work is staged and merged rather
than issuing unbounded per-row writes.

### Account deletion and GDPR

Use a hybrid strategy:

1. Immediately disable login and revoke sessions.
2. Mark the user with a non-identifying deletion tombstone.
3. Remove or irreversibly anonymize email, password hash, profile fields,
   tokens, and notification destinations.
4. Hard-delete saved-news, saved-ticket, notification, and preference rows.
5. Remove or anonymize friendships and pending requests while preserving the
   other user's usable data.
6. Preserve shared catalog content.
7. Retain only minimized, documented audit evidence with a legitimate
   retention basis.
8. Verify that personal references are removed and produce an erasure report.

The operation is idempotent and can run in bounded steps. Retention
exceptions are explicit, access-controlled, and covered by the erasure
report.

### Authentication, JWT revocation, and logout

Use short-lived access JWTs with rotating refresh tokens. JWTs contain a
subject, token ID (`jti`), issued-at time, expiry, and session/account
version.

Downstream modules verify JWT signatures locally and consult a replicated
revocation/account-status cache for:

- Disabled or deleted account status
- Session/account-version invalidation
- Explicit `jti` revocation when required

Identity publishes durable revocation events. Protected mutations fail closed
when revocation state is unavailable or too stale. Public reads may have
different requirements.

Stateless JWTs alone cannot provide zero-window revocation. If that guarantee
is mandatory, use opaque reference tokens with centralized introspection or a
central authorization layer. This ADR selects short-lived JWTs plus
replicated revocation state for the initial system and documents the
propagation-window trade-off.

### Database capacity and retry protection

The modular monolith still needs capacity controls:

- Separate web and worker pools
- Bounded worker concurrency
- Rate limits per user and operation
- Short transactions and indexed conflict paths
- Queue serialization for hot user pairs or ticket keys
- Lock, statement, and connection timeouts
- Exponential backoff with full jitter
- One retry owner per asynchronous operation
- Idempotency keys
- `429`/`503` with `Retry-After` when capacity is exhausted
- Dead-letter queues and alerts for repeated failures

Read replicas, cache-aside reads, materialized catalogue views, and CDN
caching are preferred before splitting write databases. Database partitioning
or service extraction should be driven by measured saturation and clear
ownership boundaries.

## Consequences

### Positive consequences

- Strong local consistency for social, collections, identity, and deletion
  operations
- Relational constraints prevent duplicate saves and friendships
- Lower deployment and operational complexity than microservices
- Easier integration testing and debugging
- Availability monitoring is isolated from web request execution
- Read scaling and later service extraction remain possible
- Shared GDPR workflows are easier to coordinate transactionally

### Negative consequences

- PostgreSQL remains a central capacity and availability boundary.
- Module boundaries require continuous enforcement.
- Independent domain deployment is limited.
- A database outage affects many capabilities.
- Realtime routing and revocation still require dedicated infrastructure.
- Scaling workers and web traffic independently requires pool and concurrency
  configuration.
- The system may eventually need selective domain extraction or partitioning.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Monolith becomes tightly coupled | Private persistence packages, schemas, roles, architectural tests |
| Worker starves web traffic | Separate pools, roles, limits, queues, and reserved capacity |
| Friend-request race | Deterministic pair locks, canonical key, unique constraints |
| Duplicate event/notification | Transactional outbox, stable event IDs, idempotent consumers |
| False ticket unavailability | `unknown` state, bounded retries, authoritative availability timestamps |
| Socket node failure | Managed realtime gateway, presence leases, durable replay |
| JWT remains valid after logout | Short TTL, refresh rotation, replicated revocation/account state |
| GDPR cleanup misses data | Idempotent deletion workflow, inventory, erasure report, reconciliation |
| Database write saturation | Admission control, backpressure, hot-key serialization, measured scaling |

## Implementation strategy

### Phase 1: Foundations

- Define module ownership and dependency rules.
- Create PostgreSQL schemas, roles, migrations, constraints, and indexes.
- Implement Identity with secure password hashing, sessions, refresh rotation,
  and authorization middleware.
- Establish API error contracts, structured logs, correlation IDs, metrics,
  and tracing.

### Phase 2: Core product

- Implement admin-managed Catalog.
- Implement news/ticket browsing with indexed country filtering and cursor
  pagination.
- Implement Collections with user-scoped authorization and idempotent saves.
- Implement Social with the explicit friend-request state machine and pair
  locking.

### Phase 3: Availability and notifications

- Implement current availability checks and `unknown` state.
- Add bounded availability workers and separate connection pools.
- Add persistent notifications.
- Add realtime gateway integration, presence leases, broker routing, and
  reconnect replay.

### Phase 4: Privacy and resilience

- Implement the idempotent GDPR deletion workflow and erasure report.
- Add session/account-version revocation propagation.
- Add outbox relay, retry, dead-letter, and replay tooling.
- Add overload responses, rate limits, lock timeouts, and worker backpressure.

### Phase 5: Evidence-based scaling

- Load-test reads, writes, friend-pair contention, availability checks, and
  notification fan-out.
- Measure database CPU, I/O, connections, WAL, lock waits, queue age, and
  end-to-end latency.
- Add replicas, caches, read models, or partitioning only when measurements
  and SLOs justify them.
- Reconsider Proposal 2 extraction or selective serverless use only after a
  domain has a clear ownership and scaling boundary.

## Open decisions and acceptance criteria

The following must be resolved before production approval:

- Exact ticket-availability source and freshness SLA
- Notification channel and target delivery latency
- Access-token lifetime and maximum revocation propagation window
- GDPR retention exceptions and backup expiry policy
- Availability and recovery SLOs
- Expected peak concurrency and database capacity test results
- Final reciprocal friend-request UI and state policy
- Admin roles and audit requirements

This ADR should be marked **Accepted** only after these decisions are
reviewed and the implementation strategy has measurable capacity and privacy
acceptance criteria.
