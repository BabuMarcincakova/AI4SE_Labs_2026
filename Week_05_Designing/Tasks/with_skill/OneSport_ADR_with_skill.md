# ADR-001: Select a modular monolith with a relational core for OneSport

- **Status:** Accepted
- **Date:** 2026-10-29
- **Decision owners:** OneSport engineering team
- **Scope:** Initial OneSport production architecture
- **Related records:** [Task 1 architecture review](./OneSport_Task1_with_skill.md), [discussion log](./OneSport_with_skill_discussion_log.md)

## Executive summary

| Option | Operational complexity | Transactional consistency & concurrency | Infrastructure & cost at expected scale | Time-to-market / development velocity | Assessment |
|---|---|---|---|---|---|
| Modular monolith with relational core | Lowest: one application, database, and bounded worker deployment | Strong local transactions, foreign keys, unique constraints, and deterministic locks | Predictable baseline cost; read, cache, and worker scaling remain available | Fastest initial delivery and simplest integration testing | **Selected** |
| Event-driven microservices with database per service | Highest: many runtimes, databases, broker, contracts, and runbooks | Strong within services but eventual across services; sagas and reconciliation required | Highest fixed operational cost; independent scaling helps only for measured hot domains | Slowest initial delivery and most difficult distributed debugging | Defer until independent ownership or scaling is demonstrated |
| Serverless application with managed state and workflows | Medium: less server management but substantial platform, quota, IAM, and observability complexity | Strong within bounded database transactions; workflows and retries are eventually consistent | Potentially efficient for bursty traffic, but invocation, database, queue, and egress costs are uncertain | Fast for simple handlers; slower for robust workflows, realtime, and local testing | Consider selectively if platform and workload justify it |

## Context

OneSport provides:

- Account signup, login, logout, profile access, credential changes, and
  account deletion.
- Recent sports-news browsing and upcoming sporting-event ticket browsing,
  both filterable by country.
- Saved news and saved tickets, including add, remove, view, and clear-all
  operations.
- User lookup by email, friend requests, acceptance/refusal, friend listing,
  friend details, and friend removal.

The requirements do not specify traffic volume, availability or latency
targets, geographic distribution, deployment provider, budget, content
freshness SLA, regulatory jurisdiction, moderation, or recovery objectives.
The following assumptions were confirmed during Task 1:

- OneSport displays and saves ticket offers; purchase and payment occur
  through an external provider.
- Current content is desirable, but no real-time delivery SLA is specified.
- Account deletion uses a least-retention, verifiable deletion or
  anonymization policy.

The initial system must therefore avoid scale-specific guarantees and preserve
these gaps as open decisions.

## Decision drivers

1. Keep account, saved-collection, and social operations transactionally
   correct under concurrent requests.
2. Provide an understandable and testable first production system without
   premature distributed infrastructure.
3. Make deletion, authorization, retries, and partial provider failures
   explicit and verifiable.
4. Isolate provider refresh and notification work from interactive traffic.
5. Preserve an evidence-based path to read scaling, worker scaling, or domain
   extraction.

## Considered options

### Option 1: Modular monolith with a relational core

One deployable application contains strict Identity, Content, Ticket Catalog,
Collections, Social, and Notifications modules. A relational database is the
authoritative store. Provider refresh, notification delivery, and deletion
cleanup run in bounded worker processes.

Interactive authentication, browsing, saves, and friend mutations are
synchronous. Provider refresh, notifications, retries, and long-running
deletion steps are asynchronous. Modules communicate through typed
application interfaces and selected domain events rather than direct access
to one another's tables.

The design fits because the hardest invariants are local: unique saved
entries, canonical friendships, account ownership, and credential/session
state. It is also the easiest option to develop, test, debug, and migrate
incrementally. Its costs are a shared database failure boundary, coordinated
migrations, and the need to enforce module boundaries continuously.

### Option 2: Event-driven microservices with database per service

Identity, Content, Catalog, Collections, Social, and Notifications are
independently deployed services. Each owns a database and publishes
versioned events through a broker. A gateway or BFF composes cross-service
reads.

This provides strong ownership and independent scaling, but cross-service
operations are eventually consistent. Outbox/inbox processing, idempotent
consumers, event versioning, sagas, replay, and reconciliation are required.
Account deletion must coordinate multiple databases, projections, queues,
caches, logs, and backups. This option is deferred because the requirements
do not establish independent scaling, multiple autonomous teams, or a need
for this operational cost.

### Option 3: Serverless application with managed state and workflows

An API gateway invokes stateless functions for bounded contexts. Managed
relational or document storage, queues, scheduled jobs, event buses, and
durable workflows provide state and background processing.

This can reduce server management and handle bursty workloads, but function
concurrency must be bounded by database and provider capacity. Timeouts after
commits, duplicate retries, cold starts, quota failures, platform coupling,
and emulator gaps complicate correctness and testing. It remains a
conditional option if managed-platform standardization and measured workload
characteristics make those trade-offs acceptable.

## Decision

Select **Option 1: a modular monolith with a relational core** for the initial
OneSport production system.

It wins because it provides strong local transactions for identity,
collections, and social relationships while keeping operations and
development tractable. Bounded workers and an outbox handle asynchronous
provider and notification work without making every feature distributed.
The alternatives are not rejected permanently: they become candidates when
measurements show independent scaling or fault-isolation needs, or when a
managed serverless platform is an explicit organizational constraint.

### Selected architecture

```text
                         +----------------------+
                         | Web / mobile clients |
                         +----------+-----------+
                                    |
                         HTTPS API / BFF layer
                                    |
              +---------------------v---------------------+
              | Modular OneSport application               |
              |---------------------------------------------|
              | Identity & Profile | Content / Catalog      |
              | Collections        | Social                  |
              | Notifications / Admin                       |
              +---------------------+-----------------------+
                                    |
                    typed module APIs and domain events
                                    |
              +---------------------v---------------------+
              | Relational transactional source of truth  |
              | identity | content | catalog | collections |
              | social | notifications | audit            |
              +---------------------+---------------------+
                                    |
                  transactional outbox / bounded workers
                         |                       |
              provider refresh              notifications
                         |                       |
             external content providers    optional realtime gateway
```

The realtime gateway, if required, owns live connections and presence. Domain
modules publish user- and event-oriented notifications, never a specific
application node address.

## Architecture details

### Boundaries and data ownership

The relational database is divided into owned schemas or equivalent module
boundaries:

- **Identity:** accounts, credentials, sessions, account/session versions,
  deletion state.
- **Content and Catalog:** normalized news, sporting events, ticket offers,
  provider identifiers, availability, and freshness state.
- **Collections:** saved-news and saved-ticket rows owned by the acting user.
- **Social:** friend requests and canonical friendship pairs.
- **Notifications:** durable notification records, delivery state, and
  cursors.
- **Audit:** minimized, access-controlled operational evidence.

Each module owns its persistence adapters. Cross-module reads use typed
application services or narrow read views. Separate database roles, private
persistence packages, dependency checks, and schema ownership should make
forbidden direct access fail early. Shared catalog records must not cascade
from user deletion.

### Consistency and concurrency

Use short PostgreSQL `READ COMMITTED` transactions for normal mutations.
For friend operations, normalize the pair as
`user_low_id = min(user_a, user_b)` and `user_high_id = max(user_a, user_b)`,
lock both user rows in ascending order, re-read state, apply the request
policy, and commit the transition and friendship insertion atomically.
Deterministic ordering avoids the common opposite-order deadlock.

Enforce invariants with:

- A primary key on `(user_low_id, user_high_id)` with
  `user_low_id < user_high_id`.
- A partial unique index for one pending request per directed pair.
- Unique `(user_id, news_id)` and `(user_id, ticket_id)` collection keys.
- Foreign keys, status checks, and provider-scoped content identifiers.

Retries after lost responses are safe because commands are idempotent at the
resource key or explicit idempotency-key boundary. Already-completed,
duplicate, reversed, cancelled, and invalid transitions return defined
idempotent results or conflicts rather than creating new state. Lock waits,
deadlocks, and overload are bounded, measured, and returned as explicit
retryable responses where appropriate.

### Communication and workers

Browsing and user mutations are synchronous. Provider refresh, availability
checks, notification delivery, deletion cleanup, and reconciliation are
asynchronous.

When a module changes state and emits an event, it updates its authoritative
state and inserts an outbox row in the same transaction. A relay claims rows
with a lease, publishes a stable event ID, marks the row published only after
broker acknowledgement, and retries expired leases with exponential backoff
and jitter. Repeated failures move to dead letter with operator-visible
reconciliation. Delivery is at least once; consumers deduplicate by event ID
and tolerate replay and out-of-order input.

Interactive and worker workloads use separate bounded connection pools and
database roles. Workers use bounded batches, short transactions, queue
backpressure, statement/transaction timeouts, and reserved capacity. Provider
failure is represented as stale or unknown rather than confirmed empty or
unavailable data. User responses distinguish confirmed empty results from
unavailable upstream data.

### Privacy and account lifecycle

Deletion first disables login and revokes sessions in the authoritative
Identity store. An idempotent workflow then removes or irreversibly
anonymizes email, password hashes, profile fields, tokens, notification
destinations, and personal references. Saved-news, saved-ticket,
notification, and preference rows are hard-deleted where possible.
Friendships and pending requests are removed or anonymized while preserving
the other user's usable data. Shared news and event records remain.

The workflow records bounded progress, retries safely, verifies that personal
references are gone, and produces an erasure report. Logs, traces, queues,
archives, and backups require the same inventory and retention policy.
Legitimate retention exceptions must be minimized, access-controlled, and
documented. Backup expiry and jurisdiction-specific deadlines remain open.

### Authentication, authorization, and real time

Protected operations derive the acting subject from trusted credentials, not
client-supplied user IDs. Use password hashing, credential-change
reauthentication, rate limits, short-lived access JWTs, and rotating refresh
tokens. Tokens include subject, token ID, issued-at, expiry, and
session/account version.

Downstream request verification checks signature, issuer, audience, expiry,
disabled/deleted status, session version, and targeted revoked token IDs
against replicated revocation state. Protected mutations fail closed when
revocation state is unavailable or too stale. Session/account-version
invalidation handles logout-all, credential change, and deletion; individual
token IDs handle targeted early revocation. Stateless JWTs cannot provide a
zero-window guarantee; opaque reference tokens or centralized introspection
would be required for that stronger property.

If live delivery is introduced, the gateway owns connections and records
`(user_id, connection_id, node_id, expires_at)` leases with heartbeats.
Multiple devices and tabs are supported. Notifications are persisted before
live delivery. Reconnecting clients provide a cursor or last-seen event ID
and replay missed notifications. Gateway or broker failure degrades to
delayed delivery, not a false success, and correctness does not depend on
sticky sessions.

## Consequences

### Positive consequences

- Strong local consistency for identity, collections, and social operations.
- Relational constraints prevent duplicate saves and friendships.
- Lower deployment and operational complexity than the alternatives.
- Easier integration testing, debugging, and incident response.
- Provider refresh and notification work can be isolated from web traffic.
- Read scaling, worker scaling, and later domain extraction remain possible.
- Account deletion is coordinated with fewer authoritative data stores.

### Negative consequences

- The relational database remains a central capacity and availability
  boundary.
- Module boundaries require continuous enforcement.
- Independent domain deployment and fault isolation are limited.
- Realtime routing and revocation still require dedicated durable state.
- Provider freshness, external outages, and data licensing remain operational
  concerns.
- Distributed extraction later will introduce migration and consistency work.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Monolith becomes tightly coupled | Owned schemas, private persistence packages, dependency tests, and explicit module APIs |
| Worker traffic starves interactive requests | Separate bounded pools, roles, reserved capacity, timeouts, and backpressure |
| Concurrent friend operations create duplicate or deadlocked state | Deterministic pair locks, canonical friendship key, partial unique index, and short transactions |
| Duplicate or lost asynchronous effects | Transactional outbox, stable event IDs, leases, idempotent consumers, dead letters, and reconciliation |
| Provider outage is shown as empty content | Freshness state, bounded timeouts, stale/unknown status, and truthful partial responses |
| Account deletion misses a copy | Store inventory, idempotent workflow, progress tracking, verification, erasure report, and retention controls |
| Logout or deletion leaves a token usable | Short token lifetime, refresh rotation, version invalidation, replicated revocation, and fail-closed mutations |
| Realtime delivery is lost or duplicated | Durable notification rows, connection leases, cursor replay, event IDs, and client deduplication |

## Implementation strategy

### Phase 1: Foundations

- Define module ownership, schemas, database roles, API contracts, and
  dependency enforcement.
- Implement Identity with secure password hashing, session versions, refresh
  rotation, authorization checks, and audit minimization.
- Establish migrations, backups, metrics, tracing, rate limits, and bounded
  web/worker connection pools.

### Phase 2: Core product

- Implement normalized Content/Catalog data and country indexes.
- Implement saved collections with unique keys and idempotent commands.
- Implement Social request state transitions, deterministic locking, and
  canonical friendship constraints.
- Implement browsing and explicit stale/unknown provider-data states.

### Phase 3: Resilience, privacy, and operations

- Add transactional outbox relay, leases, retry budgets, dead letters,
  replay, and reconciliation.
- Add bounded provider and availability workers with reserved capacity.
- Implement idempotent account deletion, store inventory, erasure reports,
  backup-retention policy, and verification.
- Add durable notifications and optional realtime gateway cursor replay.
- Test authorization denial, concurrent commands, lost responses, provider
  outages, stale revocation, reconnects, and partial failures.

### Phase 4: Evidence-based scaling

- Measure database CPU/I/O, connections, WAL, lock waits, transaction
  latency, queue age, provider latency, cache effectiveness, and error rates.
- Add read replicas, cache-aside reads, materialized catalog views, CDN
  caching, or additional workers only where measurements justify them.
- Reconsider service extraction or a domain-specific state store only after
  sustained saturation, clear ownership boundaries, and acceptable
  cross-domain consistency are demonstrated.

## Open decisions and acceptance criteria

- Define peak concurrency, geographic distribution, recovery point and
  recovery time objectives, and availability/latency targets.
- Confirm news and ticket provider contracts, quotas, licenses, and freshness
  requirements.
- Decide whether friend and notification updates require live delivery.
- Define country/filter semantics and behavior for incomplete provider data.
- Decide moderation, administration, abuse prevention, audit scope, and
  privacy jurisdiction.
- Define backup retention, deletion deadlines, and legitimate retention
  exceptions.
- Acceptance criterion: concurrent duplicate and reciprocal friend operations
  leave one valid canonical state and no deadlock-induced corruption.
- Acceptance criterion: state changes with lost responses can be retried
  without duplicate saves, friendships, notifications, or deletion steps.
- Acceptance criterion: account deletion blocks access immediately and
  produces verifiable completion evidence across inventoried stores.
- Acceptance criterion: provider and notification failures produce explicit
  stale/unavailable or delayed states rather than false success or empty data.

