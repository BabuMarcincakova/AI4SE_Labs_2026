# OneSport Architecture Review Log

## Session scope

This document is a maintained engineering log for the architectural discussion
requested for OneSport. It records synthesized requirements, decisions,
trade-offs, questions, and conclusions rather than a verbatim transcript.

## 2026-10-29 - Initial request summary

The user asked for a requirements-based review of the OneSport system,
including three distinct architecture proposals, their trade-offs and
low-level implementation pain points, with the discussion recorded
continuously. Only the first proposal is to be presented initially; proposals
two and three must wait for explicit direction.

## Requirements source and interpretation

Source: [OneSport.txt](./data/OneSport.txt).

OneSport is a fan-facing platform combining:

- sports news discovery, recent-news browsing, and country filtering;
- upcoming sporting-event ticket discovery and country filtering;
- authenticated accounts with signup, login, logout, profile access,
  credential changes, and account deletion;
- per-user saved collections for news and tickets, including add, remove,
  view, and clear-all operations;
- social relationships: finding a user by email, sending/accepting/refusing
  friend requests, listing friends, viewing friend details, and removing
  friends.

### Important inferred constraints

- The system has two kinds of content (news and tickets) with similar
  save/unsave behavior, but different source data and lifecycle concerns.
- Country filtering is a user-visible query capability and should be backed by
  normalized, indexed country metadata rather than client-side filtering.
- Authentication and authorization are cross-cutting concerns: private
  profiles, collections, requests, and friend lists must be isolated by user.
- Friend requests have state and concurrency rules; duplicate requests,
  self-requests, accepting an already-removed request, and opposite-direction
  requests need explicit handling.
- Account deletion has referential-integrity and privacy implications for
  saved items, requests, friendships, and any audit records.
- News and event/ticket data may be imported or refreshed from external
  providers, although the requirements do not specify providers, purchase
  settlement, payment, inventory locking, or ticket issuance. Those are
  scope questions rather than assumptions.
- The requirements describe user-facing capabilities but do not specify
  scale, availability targets, consistency guarantees, moderation, search
  relevance, notification channels, or compliance obligations. These must be
  validated before selecting a production architecture.

## Architecture Proposal 1 - Modular monolith with a relational core

### Shape

Use one deployable application with strict internal modules and one
transactional relational database:

```text
Web/mobile client
        |
   HTTPS REST API
        |
  Modular application
  | Identity & Profile
  | News
  | Events/Tickets
  | Collections
  | Social Graph
  | Content Ingestion
        |
 PostgreSQL (transactional source of truth)
        |
 Background worker / scheduled ingestion
        |
 External news and event providers
```

The modules share a process and database deployment, but communicate through
module interfaces/use cases rather than directly reaching into one another's
tables. A separate worker process can run the same application modules for
scheduled provider synchronization without requiring a distributed service
topology.

### Why it fits the current requirements

- The feature set is cohesive and transaction-heavy: saving an item,
  accepting a request, deleting an account, and updating credentials benefit
  from local database transactions.
- A relational schema naturally models users, content, collections,
  friend-request state, and the uniqueness constraints around relationships.
- A single deployable keeps the first release operationally small: one
  deployment pipeline, one authentication boundary, one database migration
  process, and straightforward local development.
- Module boundaries preserve a path to later extraction if ingestion or
  content delivery develops materially different scaling needs.
- REST endpoints can support the web UI and a future mobile client without
  exposing persistence details.

### Suggested domain model

Core tables would include `users`, `credentials` (or an external identity
reference), `news_items`, `sporting_events`, `tickets`, `saved_news`,
`saved_tickets`, `friend_requests`, and `friendships`. Provider identifiers
should be unique within a provider, while saved-collection rows should have
composite uniqueness such as `(user_id, news_id)`.

Friend requests should use an explicit state machine, for example
`pending -> accepted|declined|cancelled`, with sender, recipient, timestamps,
and a uniqueness rule preventing multiple active requests for the same
directed pair. An accepted request should create a canonical undirected
friendship, protected by a normalized pair key (for example the lower and
higher user IDs) so concurrent acceptance cannot create duplicates.

### Request and data flow examples

**Save news:** authenticate the user, authorize the requested news item as
visible, insert into `saved_news` with an idempotent uniqueness conflict
response, and return the saved resource. Removing it is a user-scoped delete.

**Accept friend request:** load the pending request with a row lock, verify
the recipient is the current user, transition the request, and insert the
canonical friendship in one transaction. A second concurrent acceptance
should return the already-accepted result or a clear conflict, never create a
duplicate friendship.

**Refresh content:** a worker fetches provider pages using a bounded timeout,
validates and normalizes records, upserts by provider identity, marks stale
records according to a documented policy, and records failures/metrics. User
queries read the normalized database and do not depend on provider latency.

### Primary trade-offs

**Advantages**

- Low operational and development complexity.
- Strong consistency for collections, social actions, and account lifecycle.
- Simple end-to-end testing and debugging.
- Shared transactions and foreign keys prevent many integrity defects.
- Clear incremental scaling options: read replicas, caching, worker scaling,
  and eventually extracting ingestion or search.

**Costs**

- The application is a larger codebase and requires disciplined module
  boundaries; a monolith can become a "big ball of mud" without enforcement.
- A database outage affects most capabilities.
- Independent deployment and scaling of news, tickets, and social features are
  limited compared with microservices.
- Provider ingestion failures and slow external APIs still require careful
  isolation from request handling.
- A single relational schema creates coordination cost for migrations and
  ownership as the team grows.

### Low-level implementation pain points

1. **Authentication security:** password hashing (Argon2id or equivalent),
   secure session/token rotation, credential-change reauthentication,
   logout/revocation semantics, rate limiting, email uniqueness, and account
   deletion must be implemented deliberately. Passwords must never be stored
   directly.
2. **Authorization leakage:** every collection, request, and friend endpoint
   must derive the acting user from verified authentication, not a client
   supplied user ID. Tests should cover IDOR-style access attempts.
3. **Relationship races:** unique indexes, transactions, row locks or
   optimistic version checks, and idempotent commands are needed for duplicate
   requests and concurrent accept/delete operations.
4. **Content identity:** external providers may change titles, URLs, country
   labels, or event times. Provider IDs, source attribution, normalization,
   timezone handling, deduplication, and stale-record policy need explicit
   rules.
5. **Pagination and filtering:** use stable cursor pagination for news and
   tickets, indexed country/status/time columns, bounded page sizes, and
   deterministic ordering. Avoid loading entire collections into memory.
6. **Account deletion semantics:** decide whether data is hard-deleted,
   anonymized, or retained for legal/audit reasons. Foreign-key cascades must
   not accidentally delete shared content or historical relationship records.
7. **Worker reliability:** external calls need timeouts, retry limits,
   backoff, idempotent upserts, deduplicated jobs, and observable dead-letter
   handling. A failed refresh must not silently erase good content.
8. **API evolution and observability:** define error codes, validation
   responses, correlation IDs, structured logs, metrics, and migration/backfill
   procedures before clients depend on the API.

### Questions to resolve before selecting this architecture

- Is ticket purchase merely saving/redirecting to a provider, or must OneSport
  own inventory, checkout, payment, refunds, and ticket issuance?
- Which providers supply news and event data, and what are their rate limits,
  licensing terms, freshness targets, and failure behavior?
- What are expected user/content volumes, peak traffic, and availability/SLO
  requirements?
- Are notifications (email, push, or in-app) required for requests or events?
- What privacy, retention, moderation, and account-deletion obligations apply?

## Discussion status

Proposal 1 has been presented for review. Proposal 2 is intentionally
deferred until the user explicitly requests it.

## 2026-10-29 - Product clarifications and Proposal 1 deep dive

### User clarification summary

The user clarified that OneSport displays and saves ticket offers but does not
sell tickets. News and event data are entered or maintained by an admin group,
not fetched from external providers. New-ticket availability must be checked
when the catalogue is viewed. Availability of saved tickets must be checked at
login and continuously enough to notify users immediately after an offer
becomes unavailable. The expected scale is tens of thousands of users, and
GDPR-compliant account deletion is required. Other unspecified product
decisions may use sensible defaults.

These clarifications reduce the ingestion-provider complexity in Proposal 1,
but introduce a high-priority availability-monitoring and notification
workflow. A practical default is a database-backed admin content-management
interface, a separate availability-monitoring worker, and an in-app
notification mechanism, with email/push treated as a later channel.

### Decisions and implementation notes from the deep dive

#### Database coupling and module boundaries

Use schema ownership and application-enforced module APIs together:

- Give each module an owned PostgreSQL schema, such as `identity`,
  `catalog`, `collections`, `social`, and `audit`.
- Grant the application database role access only to the schemas it needs;
  use separate module roles for migrations and controlled views where
  cross-module reads are unavoidable.
- Keep tables private to their owning schema. Expose read models or narrowly
  scoped SQL views rather than granting arbitrary table access.
- Enforce code boundaries with one repository/package per module, private
  persistence adapters, and architectural dependency tests that reject imports
  from another module's persistence package.
- Cross-module actions go through typed application services or domain events,
  not direct table joins. A transaction coordinator may call multiple
  application services when atomicity is required.
- Treat PostgreSQL row-level security as defense in depth for user-owned data,
  not as a substitute for module ownership. CI should test grants and forbidden
  cross-schema references.

This does not make a shared database physically independent, but it makes
ownership explicit and makes accidental bypasses fail during development,
migration, or deployment rather than silently becoming architecture.

#### Concurrent friend requests

Use PostgreSQL `READ COMMITTED` as the normal isolation level, explicit
unique indexes, and a short transaction that locks a deterministic pair of
user rows. The pair lock serializes opposite-direction requests for the same
two users; the unique constraints are the final safety net.

For an accepted request, the transaction locks both user rows in ascending
user-ID order, locks the relevant pending request rows, verifies state and
authorization, then inserts the canonical friendship
`(user_low_id, user_high_id)`. The friendship primary key or unique index
ensures only one friendship exists. Locking in the same order prevents
deadlocks. A unique conflict is handled as an idempotent already-friends
result or a clear conflict, never as an unhandled server error.

For simultaneous A-to-B and B-to-A requests, both transactions contend on the
same deterministic pair lock. One completes first; the second re-reads the
current state and applies the documented policy (for example, automatically
consolidate reciprocal pending requests into one pending relationship or
accept only after an explicit action). The exact policy must be selected
before implementation.

#### Worker isolation and connection pooling

Run availability checking and admin-content processing in a separate worker
deployment with a distinct PostgreSQL role and connection pool. Set a hard
pool maximum and database statement/transaction timeouts. Use bounded batches,
short transactions, queue backpressure, and keyset pagination. Never hold a
transaction open across an external availability check.

Reserve capacity for web traffic using separate pools and, if necessary,
PostgreSQL connection limits or a separate read replica for catalogue reads.
Use priority-aware queues so availability checks and notification delivery
cannot be overwhelmed by bulk admin imports. Bulk writes should be staged,
validated, and merged in controlled batches rather than issuing unbounded
per-row upserts. Monitor pool utilization, query latency, lock waits, and
worker lag.

#### GDPR account deletion

Use a hybrid strategy: immediately deactivate and anonymize the account in a
short transaction, hard-delete user-owned operational data that has no
retention reason, and retain only strictly necessary, minimized audit evidence.

The user row receives a non-identifying tombstone (for example a generated
deletion subject), `deleted_at`, and disabled authentication. Email,
password hashes, sessions, tokens, profile fields, and notification
destinations are removed or irreversibly anonymized. Saved-news and
saved-ticket rows, notifications, and personal preferences are hard-deleted.
Friendships and pending friend requests are removed or transitioned to an
`account_deleted` state while preserving the other party's usable data.
Shared news, events, tickets, and admin audit records are not cascaded from
the user row.

Deletion is implemented as an idempotent workflow: disable access first,
record a minimal deletion job, clean dependent data in bounded steps, and
verify that no personal references remain. Retention exceptions must be
explicit, documented, access-controlled, and covered by an erasure report.

## 2026-10-29 - Architecture Proposal 2 request

The user requested a fundamentally different second architecture, including
its service decomposition, synchronous and asynchronous communication model,
trade-offs, and low-level implementation pain points. This proposal is
deliberately contrasted with Proposal 1's modular monolith.

## Architecture Proposal 2 - Event-driven microservices with database-per-service

### Shape

OneSport is split into independently deployable services. Each service owns
its database and publishes integration events through a durable message
broker:

```text
 Web/mobile clients
        |
 API gateway / BFF
        |
  +-----+-----------+-----------+-------------+
  |                 |           |             |
Identity        Catalog      Collections   Social
service         service      service       service
  |               |           |             |
 DB              DB          DB            DB
  |               |
  +--------+------+ 
           |
      Event broker
           |
  +--------+-------------+------------------+
  |                      |                  |
Availability        Notification       Audit/
monitor             service             analytics
service             DB                  sink
  |                      |
  DB                 WebSocket/SSE,
                     email/push adapters
```

The API gateway authenticates requests and routes them to services. It may
also expose a backend-for-frontend (BFF) that composes independently owned
read models for screens such as a user's saved-ticket page. No service reads
another service's private tables.

### Service responsibilities

#### Identity service

Owns accounts, credentials, sessions, GDPR deletion initiation, and the
identity lifecycle. It publishes events such as `UserRegistered`,
`UserDeactivated`, and `UserDeletionCompleted`. Other services store only the
minimum user reference and a local anonymized projection needed for their own
authorization or display.

#### Catalog service

Owns admin-managed news, sporting events, ticket offers, countries, and the
current availability state. Admin commands are synchronous because the admin
needs validation and a definitive response. Catalog changes also publish
events such as `TicketOfferAvailabilityChanged`.

#### Collections service

Owns saved-news and saved-ticket relationships. It accepts commands such as
`SaveTicket` and `RemoveSavedTicket`. It subscribes to catalog availability
events and maintains a local projection of the availability of saved offers.
This lets it answer a saved-ticket query without joining to the catalog
database.

#### Social service

Owns friend requests and friendships. It serializes relationship commands for
each user pair and publishes events such as `FriendRequestAccepted` and
`FriendshipRemoved`.

#### Availability-monitor service

Checks the active ticket-offer set on a bounded schedule, or consumes an
admin-originated change stream if administrators directly control
availability. It sends commands to the catalog service or receives catalog
events, then publishes availability transitions. It must distinguish a
confirmed unavailable offer from a temporary failed check.

#### Notification service

Consumes availability and social events, applies per-user deduplication, and
stores durable in-app notifications. It delivers them through WebSocket or
Server-Sent Events when the user is online, with email/push adapters as
optional later channels.

#### Audit and analytics sink

Consumes immutable, privacy-minimized events. It must not become a hidden
source of personal data that defeats GDPR deletion.

### Synchronous communication

Use synchronous HTTPS or gRPC for operations requiring an immediate answer:

- Login and credential validation
- Admin creation or editing of catalog content
- Browsing current news and ticket offers
- Saving or removing a collection item
- Sending, accepting, declining, or deleting a friend request
- Loading a user-facing page when a current read model is available

The caller receives a success or explicit error from the owning service. A
gateway should not perform distributed database transactions behind an
apparently simple request.

For a page requiring multiple services, the BFF can issue parallel reads and
return a composed response. It must define partial-failure behavior instead
of hiding a missing service behind empty success-shaped data.

### Asynchronous communication

Use a durable broker for work that can complete after the initial command:

- Catalog changes and availability transitions
- Notification creation and delivery
- Updating collections' local availability projections
- Friend-request notifications
- Audit events
- GDPR erasure propagation
- Search or analytics projections

The event flow for a ticket becoming unavailable is:

```text
Availability monitor
  -> Catalog: update availability (command)
  -> Catalog: TicketOfferAvailabilityChanged (event)
  -> Collections: update saved-offer projection
  -> Notifications: create one user notification
  -> Delivery adapter: push WebSocket/SSE/email notification
```

At login, the gateway can synchronously ask Collections for saved-ticket
state and its `last_verified_at` values. If an offer is stale, Collections
can return that fact and enqueue a verification command, or the availability
service can refresh it before the response when the freshness SLA permits.
The continuous monitor remains responsible for near-real-time changes.

### Consistency model

Each service is strongly consistent within its own database transaction.
Cross-service state is eventually consistent. Events must be delivered at
least once, so every consumer needs an idempotency key such as
`(event_id, consumer_name)` or a domain-specific transition key.

Use the transactional outbox pattern in every event-producing service:

1. Update the service's state.
2. Insert the event into an outbox table in the same local transaction.
3. A publisher forwards outbox rows to the broker.
4. Consumers acknowledge only after their local transaction succeeds.

Consumers should use inbox records or equivalent deduplication so broker
redelivery does not create duplicate notifications or repeated state changes.

### Major advantages

- Services can scale independently; availability checks cannot consume the
  catalog API's process memory or web request threads.
- Database-per-service creates a stronger ownership boundary than a shared
  PostgreSQL instance.
- Brokered events naturally support immediate availability notifications and
  future channels.
- Individual services can be deployed or rolled back independently.
- Failures can be isolated and retried, provided event contracts are robust.
- The architecture supports future high-volume notification, search, or
  catalog workloads without scaling identity and social code unnecessarily.

### Major trade-offs

- Much higher operational complexity for a product whose core domain is still
  relatively small.
- Cross-service reads are eventually consistent and require projections,
  reconciliation, and explicit stale-data UX.
- Cross-service transactions are replaced by sagas and compensating actions.
- Debugging requires distributed tracing, correlation IDs, broker inspection,
  and replay tooling.
- Every service needs deployment, health checks, dashboards, secrets,
  migrations, and incident procedures.
- Database-per-service can duplicate user and catalog data, increasing storage
  and synchronization complexity.
- Local development and end-to-end testing need a broker and multiple service
  processes, or carefully maintained test doubles.

### Low-level implementation pain points

1. **Friend-request atomicity without a shared database:** Social can make its
   own request/friendship transition atomic, but identity validation and
   notification delivery are separate. A deleted user may race with a social
   command. Social needs a local identity projection, versioned user lifecycle
   events, and a policy for commands received during projection lag.
2. **Saved-ticket availability races:** Collections may receive
   `TicketOfferAvailabilityChanged` after a user reads an old state. Responses
   need `observed_at`/`last_verified_at` timestamps, and the UI must distinguish
   unavailable from unknown or stale. Catalog remains authoritative.
3. **Event delivery semantics:** At-least-once delivery means duplicate
   events, out-of-order events, consumer retries, poison messages, dead-letter
   queues, and replay behavior must be designed. A broker publish acknowledgement
   is not proof that every consumer has applied the event.
4. **Outbox and schema evolution:** Each service needs outbox cleanup,
   publisher retry, event versioning, backward-compatible consumers, and a
   retention policy. Renaming a field in an event can break an independently
   deployed older consumer.
5. **No distributed transactions:** A save command succeeding while its
   notification or projection update fails is normal. Sagas, reconciliation
   jobs, and user-visible pending states are required; two-phase commit should
   not be introduced casually.
6. **Gateway failure semantics:** A composed response can contain fresh catalog
   data but stale collections data. The BFF needs deadlines, parallel call
   limits, circuit breakers, explicit partial responses, and no fabricated
   empty lists.
7. **GDPR erasure propagation:** Identity can revoke access immediately, but
   deletion events must reach every service and retained event/archive store.
   The system needs an erasure ledger, replay-safe deletion handlers, bounded
   completion targets, and verification across databases and backups.
8. **Availability-monitor overload:** Partition the offer stream, rate-limit
   checks, use leases or a scheduler, and ensure one offer is not checked by
   multiple workers concurrently. A source outage must not turn every offer
   into `unavailable`; represent `unknown` and preserve the last confirmed
   state.
9. **Operational security:** Service-to-service authentication, broker ACLs,
   secret rotation, tenant/user authorization in every service, and prevention
   of confused-deputy calls are mandatory. The gateway is not a substitute
   for authorization inside services.
10. **Testing and recovery:** Contract tests, consumer-driven event tests,
   replay tests, failure injection, backup/restore drills, and cross-service
   tracing are needed before this architecture is dependable.

### Suitability assessment

This architecture is technically appropriate if OneSport expects the
availability monitor, notifications, or catalog workloads to grow
independently, or if multiple teams need autonomous deployment. For the
currently stated tens-of-thousands-of-users scale, it is likely more
expensive than Proposal 1. Its strongest justification is organizational or
operational independence, not raw user volume alone.

Proposal 2 has now been presented. Proposal 3 remains intentionally deferred
until the user explicitly requests it.

## 2026-10-29 - Proposal 2 failure-mode deep dive

The user challenged four high-risk distributed-systems concerns. The agreed
design principles are: an outbox is a durable local obligation rather than a
best-effort buffer; GDPR deletion is tracked as a deadline-driven workflow
with independent verification; event contracts are evolved additively with
compatibility gates; and BFF responses distinguish unavailable sections from
empty data.

### Transactional outbox publisher failure

If a service commits its business state and outbox row but the publisher
crashes before broker publication, the event is not silently lost: it remains
pending in the service database. Recovery requires an always-on relay
deployment, polling/notification wakeups, retry metadata, and operational
metrics. The relay claims rows with leases, publishes with a stable event ID,
marks them published only after broker acknowledgement, and safely retries
expired claims. Duplicate publication is acceptable and is handled by
consumer idempotency.

Use an outbox state such as `pending`, `publishing`, `published`, and
`dead_letter`, with `attempt_count`, `next_attempt_at`, `lease_until`,
`last_error`, and timestamps. A watchdog finds overdue `publishing` rows and
returns them to `pending`. Exponential backoff, alert thresholds, a durable
dead-letter state, and a replay tool make failures observable and recoverable
without editing production tables manually. A broker-side confirm proves
acceptance by the broker, not successful processing by every consumer.

### GDPR erasure across service databases

Do not treat a single deletion event as proof of erasure. Identity first
blocks authentication and issues a deletion case with a legal deadline and
required service acknowledgements. A durable erasure coordinator/outbox
records the participating services and sends versioned deletion commands.
Each service performs an idempotent local purge/anonymization transaction,
records an erasure receipt, and retries until completion.

Offline services are safe because commands remain in the broker/outbox and
are replayed. The coordinator continuously tracks deadline risk, alerts on
stalled services, and can disable dependent functionality immediately using
the identity tombstone. It must not report completion until all required
stores acknowledge, including notification, analytics, search, archives, and
backup-retention handling. A compensation saga is useful for retries and
repair, but cannot undo a deletion or substitute for verification.

The legally defensible design is a deadline-driven erasure ledger plus
automated reconciliation and escalation, not a blocking distributed
transaction. Backups require a documented retention/expiry policy; data
remaining in immutable backups must be inaccessible and naturally expire
within the approved retention period.

### Event schema evolution

Use immutable, versioned event contracts with additive evolution:

- Every event has an event type, schema version, event ID, producer, subject,
  occurred-at timestamp, correlation ID, and payload.
- A field rename is treated as a new field or new event version, not an
  in-place rename.
- Producers publish old and new representations during a migration window.
- Consumers read the old contract and tolerate unknown fields before the new
  contract is activated.
- Contract tests run in CI against all registered consumers.
- A schema registry or equivalent artifact repository validates compatibility
  and blocks incompatible publication.
- Metrics identify consumers still using the old version; removal requires a
  deprecation deadline and proof of migration.

For `TicketOfferAvailabilityChanged`, retain the old field while adding the
replacement, for example `available` plus `availability_status`. Consumers
prefer the new field when present and fall back to the old field. Only after
all consumers migrate can the old field be removed in a new major schema
version. Unknown fields must be ignored, while missing required fields must
cause an explicit retry/dead-letter outcome rather than a guessed default.

### BFF partial-failure UX

The BFF must have a per-dependency deadline shorter than the overall request
deadline and return section-level status. If Notifications times out while
Catalog and Collections succeed, the response should contain the real catalog
and saved-ticket data plus a notification section marked unavailable, for
example:

```json
{
  "catalog": {"status": "ok", "items": []},
  "savedTickets": {"status": "ok", "items": []},
  "notifications": {
    "status": "temporarily_unavailable",
    "items": null,
    "retryable": true
  },
  "degraded": true
}
```

`items: []` means a confirmed empty result; `items: null` with an error status
means the section was not obtained. The UI should show a non-blocking banner
such as "Notifications are temporarily unavailable" and retain cached
notification data with a stale marker if safe. It must never infer that saved
tickets are empty from a notification timeout.

Prevent cascading timeouts with strict per-call deadlines, cancellation,
bounded parallelism, circuit breakers, bulkheads, and a small overall budget.
Do not retry synchronously inside the BFF more than once; use asynchronous
recovery or client refresh. Catalog and Collections are core sections and
should have independently defined fail-open/fail-closed behavior. BFF metrics
must record section latency, timeout rate, and degraded responses.

## 2026-10-29 - Architecture Proposal 3

The user requested the third and final architecture, including its high-level
structure, interaction between stateless functions and stateful services,
trade-offs, and low-level implementation pain points. The distributed
failure-mode decisions above remain part of the running review.

## Architecture Proposal 3 - Serverless application with managed state and workflows

### High-level structure

Proposal 3 uses managed cloud primitives instead of long-running application
servers or independently operated microservice runtimes:

```text
 Web/mobile clients
        |
 CDN / WAF / API gateway
        |
 Stateless functions
  | Auth and profile handlers
  | Catalog queries and admin commands
  | Collection commands
  | Social commands
  | BFF/read handlers
        |
  +-------------------+-------------------+
  |                   |                   |
 Managed SQL      Managed cache       Object storage
 database         / read models       / admin imports
  |                   |
  +---------+---------+
            |
      Managed event bus / queues
       |       |        |       |
  Workflow  Availability  Notification  Audit
  engine    functions     functions     sink
```

Functions are stateless and short-lived. Durable state lives in managed
services: a relational database for transactions, queues/events for
asynchronous work, a cache for selected reads, object storage for imports and
exports, and a workflow engine for long-running processes.

This is not simply placing the monolith in functions. Handlers must tolerate
retries, timeouts, duplicate delivery, cold starts, and arbitrary placement
on different runtime instances.

### Stateful components

#### Managed relational database

Use managed PostgreSQL-compatible storage as the source of truth for users,
credentials, admin-managed news and tickets, saved collections, friendships,
friend requests, notifications, and workflow/outbox state where transactional
publication is required.

Managed hosting reduces infrastructure administration but does not remove
schema constraints, transaction design, migrations, backup/restore drills, or
the module ownership rules established in Proposal 1.

#### Queues, event bus, and workflow engine

Use separate queues or topics for availability checks, availability
transitions, notification delivery, friend-request notifications, GDPR
commands, and audit events. A durable workflow engine coordinates account
deletion, scheduled availability verification, bulk admin imports, and
notification retry/escalation.

Queue messages require bounded retries and dead-letter queues. Workflow state
must be externalized; a function process may crash at any point.

#### Cache, read models, and object storage

Cache popular recent-news and ticket responses with explicit TTLs and
invalidation. The cache must never be the only source of truth. Materialized
read models can optimize high-volume screens but must be rebuildable.

Object storage is suitable for admin CSV/JSON imports and exports. Personal
data placed there needs lifecycle, access-control, and erasure rules; managed
storage is not automatically GDPR-safe.

### Stateless functions

Functions are organized around use cases such as:

```text
LoginUser
UpdateCredentials
BrowseNews
BrowseTicketOffers
SaveTicket
RemoveSavedTicket
SendFriendRequest
AcceptFriendRequest
DeleteAccount
AdminUpdateTicketAvailability
DeliverNotification
```

Each invocation authenticates and authorizes the request, validates input,
uses a bounded deadline, performs a short transaction or enqueues durable
work, and returns an explicit consistency/freshness indicator.

Functions must not store session state in process memory or depend on a warm
instance. Any connection reuse is an optimization, not a correctness
assumption.

### Interaction between state and functions

For a ticket browse request:

```text
Client -> API gateway -> BrowseTicketOffers function
       -> cache or managed database
       -> availability, last_checked_at, and response
```

The function owns no durable result; the database or cache does.

For availability monitoring:

```text
Scheduler -> availability-check queue -> check function
          -> source -> short database transaction
          -> availability-changed event -> notification function
```

Each job has an idempotency key and visibility lease. Failed invocations
become visible again or move to a dead-letter queue after bounded retries.

For GDPR deletion:

```text
DeleteAccount function
  -> revoke identity synchronously
  -> start durable deletion workflow
  -> invoke deletion functions
  -> wait for receipts and verify stores
  -> mark erasure complete
```

The workflow engine stores the current step, deadline, retry count, and
receipts; no function relies on its own memory surviving.

### Communication model

Use synchronous API calls for login, current catalogue reads, save/remove
operations, friend-request commands, and admin edits. Use asynchronous queues
and events for availability monitoring, notifications, bulk imports, GDPR
propagation, audit processing, and cache/read-model refreshes.

Avoid long synchronous function-to-function chains. They create cascading
failure and latency coupling similar to microservices while retaining
serverless timeout and debugging problems.

### Major advantages

- No application-server fleet to patch, scale, or keep running.
- Automatic scaling for bursty browsing and availability checks.
- Pay-per-use can suit uneven workloads.
- Managed queues and workflows provide durable retries and scheduling.
- Stateless handlers are easy to replace and replicate.
- Per-function permissions can enforce least privilege.
- A managed PostgreSQL core preserves transactions for collections and social
  operations.

### Major trade-offs

- Strong dependency on the cloud provider's gateway, functions, database,
  queues, and workflow semantics.
- Cost can become unpredictable through high invocation volume, chatty calls,
  database connection churn, or excessive event transitions.
- Cold starts and platform scheduling cause latency variance.
- Local behavior differs from production IAM, networking, event delivery, and
  timeout behavior.
- Fine-grained functions can recreate microservice complexity without useful
  domain boundaries.
- WebSocket/SSE delivery needs a managed connection service or separate
  gateway component.
- Vendor-specific workflows and events make migration harder.
- Short-lived asynchronous execution is difficult to observe end to end.

### Low-level implementation pain points

1. **Database connection exhaustion:** Bursts can create one connection per
   invocation. Use a connection proxy, strict concurrency limits, short
   transactions, and reserved capacity for interactive requests.
2. **At-least-once invocation:** A function can be retried after committing
   successfully. Commands require idempotency keys, unique constraints, and
   safe client retries.
3. **Timeout after commit:** A function may time out after committing but
   before returning. Command APIs should accept idempotency tokens and allow
   clients to safely query the command result.
4. **Availability scheduling:** Do not enqueue unbounded checks. Use sharded
   schedules, queue leases, per-source rate limits, a next-check index, and
   separate `unknown` and `unavailable` states.
5. **Real-time notifications:** Functions should not hold long-lived sockets.
   Persist notification events first, use managed WebSocket/SSE delivery, and
   replay missed notifications after reconnect.
6. **Workflow retries:** Every workflow step needs an idempotency key,
   timeout, receipt, and repair behavior. A workflow timeout is not erasure
   completion.
7. **GDPR across managed services:** Include rows, cache entries, object
   artifacts, logs, traces, queues, workflow history, and backups in the
   data inventory. Configure redaction and retention before launch.
8. **Cold starts and dependency size:** Keep handlers small and define latency
   budgets without weakening validation or authorization.
9. **IAM and secrets:** Use least-privilege generated roles, secret rotation,
   and automated tests for denied access. Too many ad hoc policies become
   unreviewable.
10. **Testing and replay:** Test retries, duplicate deliveries, expired
    leases, workflow resumption, dead-letter replay, and provider outages.
    Replay must not resend notifications or undo deletion.
11. **Infrastructure-as-code drift:** Version gateways, queues, permissions,
    schedules, alarms, and migrations together; avoid manual console changes.
12. **Cost observability:** Track invocations, duration, memory, queue
    messages, workflow transitions, database I/O, cache operations, and
    egress. Small per-invocation inefficiencies multiply at scale.

### Suitability assessment

Proposal 3 is attractive when the team wants minimal server operations,
bursty workloads, managed reliability primitives, and a cloud-first product.
It is a reasonable alternative if the team accepts vendor coupling and
invests in infrastructure-as-code, observability, and idempotent workflows.

For OneSport, it may reduce infrastructure staffing compared with
microservices, but it is not automatically simpler than the modular monolith.
The managed database remains a critical shared state component, and the
function/event boundary retains many distributed-systems failure modes.

Proposal 3 has now been presented. All three proposals are recorded; a final
consolidated comparison and recommendation can be produced when requested.

## 2026-10-29 - Proposal 3 database bottleneck and retry-storm review

The user challenged whether auto-scaling functions backed by one managed
relational database merely create a distributed monolith. The conclusion is
that an unbounded function fleet connected directly to one database would
indeed create a database bottleneck. Serverless scaling must therefore be
decoupled from database concurrency, and Proposal 3 should be treated as a
phased architecture rather than an unlimited scale promise.

### Why the database becomes the bottleneck

Function concurrency can grow much faster than the database can accept
connections, row locks, WAL writes, or transaction work. Friend requests and
ticket saves are write-heavy and contend on user-pair or user-item uniqueness
constraints. Workflow state and notification writes add further pressure. A
connection proxy prevents connection storms but does not create more database
CPU, I/O, or lock capacity.

The dangerous design is:

```text
unbounded function concurrency -> one connection per invocation
                                -> database saturation
                                -> timeouts and retries
                                -> even more concurrent work
```

That is a distributed monolith in the operational sense: compute scales
independently, but correctness and throughput remain constrained by one
central write authority.

### Required protection before production

Use admission control between functions and the database:

- Put hard reserved and maximum concurrency on write functions.
- Use a managed connection proxy with a bounded database connection pool.
- Reserve separate capacity for interactive writes, reads, and background
  workflows; do not let availability checks consume all slots.
- Return `429 Too Many Requests` or an explicit retryable response when the
  system is at its write budget. Do not allow unlimited waiting.
- Keep transactions short, index conflict paths, and avoid holding locks while
  calling other services.
- Use queue-based serialization for hot aggregates such as one user's
  friendship pair or a heavily saved ticket.
- Apply token-bucket or leaky-bucket rate limits per user and per operation.
- Use circuit breakers that stop sending work to a saturated database.
- Monitor connections, transaction latency, lock waits, deadlocks, CPU, I/O,
  WAL volume, queue age, and rejected requests.

The function platform's maximum concurrency must be configured from measured
database capacity, not from peak theoretical HTTP demand. A queue can absorb
bursty asynchronous work, but synchronous commands still need bounded
admission and a clear overload response.

### Retry storms under connection or lock pressure

A serverless retry storm occurs when many invocations fail or time out while
waiting for a connection or row lock, and the platform or client retries them
simultaneously. Retries then compete with the original work, increasing lock
queues and exhausting connections further.

The required retry policy is:

1. Classify errors. Retry transient network failures, deadlocks, and explicitly
   retryable overload responses; do not retry validation, authorization, or
   permanent constraint errors.
2. Use exponential backoff with full jitter and a strict retry budget.
3. Respect queue visibility timeouts and platform retry limits.
4. Do not retry immediately inside every layer. Choose one retry owner:
   the queue, workflow engine, or API client for a given operation.
5. Bound database lock and statement waits so an invocation fails fast enough
   to release capacity.
6. Use idempotency keys so a retry after an unknown commit outcome cannot
   duplicate a save, request, notification, or deletion step.
7. Send repeatedly failing messages to a dead-letter queue and alert rather
   than retrying forever.

For synchronous HTTP commands, return a documented `503` or `429` with
`Retry-After` when capacity is exhausted. For asynchronous commands, retain
the message durably and retry later. Never turn a lock timeout into a rapid
busy loop.

### Lock-contention strategy

For friend requests, serialize operations on a deterministic user pair using
the same ordered lock policy described for Proposal 1. For collection saves,
use unique keys such as `(user_id, ticket_id)` and keep the insert transaction
short. If a single ticket or user becomes a hot key, route commands for that
key through a partitioned queue so only one worker processes that partition
at once.

This improves contention behavior but does not increase the maximum write
throughput of the relational database. It converts uncontrolled contention
into visible, measurable queueing.

### Scaling beyond one relational write authority

Read scaling can be introduced first:

- Read replicas for news and ticket catalogue queries
- Cache-aside reads with bounded TTLs
- Materialized catalogue read models
- CDN caching for public content

Write scaling is more difficult because collections, social relationships,
and GDPR deletion need transactional integrity. Possible later evolution is:

- Keep Identity/Social in a strongly consistent relational store.
- Move catalogue reads to a separate read model fed by admin changes.
- Store availability transitions in an append-oriented stream or partitioned
  store, while retaining a current-state projection.
- Partition collections by user ID if volume justifies it.
- Use separate databases only after identifying a domain with clear ownership
  and acceptable cross-domain consistency.

Do not split the database merely to claim horizontal scaling. Cross-database
friendship transactions and GDPR erasure become substantially harder. The
decision should be driven by measured write saturation, lock contention, and
service-level objectives.

### Revised suitability conclusion

Proposal 3 is viable for OneSport only with an explicit database-protection
layer and bounded function concurrency. For the expected tens of thousands of
users, a managed relational database may be sufficient if catalogue reads are
cached or replicated and writes are rate-limited. "Instant auto-scaling" must
not mean unlimited concurrent database transactions.

If measurements show sustained write saturation, the next step should be
selective partitioning or a domain-specific state store, not indiscriminate
function scaling. This reinforces the comparative advantage of Proposal 1:
its application-level concurrency is easier to regulate. Proposal 3 reduces
server operations, but it does not eliminate capacity planning for the
database.

## 2026-10-29 - Cross-cutting real-time routing and token revocation review

The user identified two unresolved leaks affecting both the microservices and
serverless proposals: routing an event to the process holding a user's live
WebSocket/SSE connection, and making logout/GDPR revocation effective when
downstream services validate stateless JWTs locally.

### Real-time connection routing

Socket ownership must be separated from business-event processing. No Catalog,
Social, or Availability worker should know which container or gateway node
holds a socket. Use a managed realtime gateway or a dedicated connection
service backed by a distributed presence registry and a pub/sub broker:

```text
Client -> load balancer -> realtime gateway node
                              |
                 connection registry/presence
                              |
Domain event -> notification router -> pub/sub topic
                              |
               gateway node holding the connection
                              |
                            Client
```

On connect, the connection service authenticates the user, creates a
connection ID, and records `(user_id, connection_id, node_id, expires_at)` in
a registry with a lease/heartbeat. The node subscribes to the broker or to a
user/partition channel. On disconnect or lease expiry, the presence entry is
removed. A user may have multiple connections, devices, or tabs, so routing
must fan out to all currently valid connection IDs.

When a ticket or friendship event occurs, the producer publishes a durable
notification event containing the user ID and event ID, not a node address.
The notification router looks up active presence and publishes to the
appropriate user/partition channel. Any gateway node can receive the message
and deliver it only to its locally held sockets. A managed WebSocket/SSE
service can provide this routing without OneSport operating the registry
itself.

Delivery is at least once and live delivery is not a durable guarantee. Write
the notification to the Notifications store before attempting the socket
push. On reconnect, the client sends a cursor or last-seen event ID and
replays missed notifications from durable storage. Use event IDs and client
deduplication to prevent duplicate UI effects. Presence entries need TTLs,
bounded registry cardinality, and cleanup for crashed nodes.

Avoid putting node IDs in domain events or using sticky sessions as the
correctness mechanism. Sticky sessions can improve locality but do not solve
node failure, reconnects, multi-device fan-out, or autoscaling.

### JWT revocation and immediate account blocking

Purely self-contained JWT validation cannot provide instant revocation: a
valid, unexpired token remains cryptographically valid. The design must add a
revocation signal or change the token strategy. Do not make every request call
Identity synchronously; that creates a latency and availability dependency.

Use short-lived access tokens (for example 5-10 minutes) plus rotating refresh
tokens, and combine them with a distributed revocation/account-status cache
replicated to every request-verifying service or edge authorizer. The token
contains a subject, token ID (`jti`), issued-at time, and an account/session
version. Identity publishes `SessionRevoked` and `UserDeactivated` events
through a durable broker. A revocation consumer updates the local cache:

```text
Identity -> durable revocation event
         -> edge/service cache: user status, session version, revoked jti
         -> local JWT verification + local revocation check
```

Each downstream service verifies signature, issuer, audience, expiry, and
claims locally, then checks the local cache for:

- disabled/deleted user status;
- token/session version newer than the token's version;
- explicitly revoked `jti` where individual-token revocation is required.

The cache needs a defined fail policy. For protected mutations, fail closed
when the account-status data is unavailable or stale beyond its maximum age.
For low-risk public reads, no account-status lookup may be needed. Include a
bounded TTL and a last-synchronized version so stale caches are detectable.

There is an unavoidable propagation window between Identity's revocation and
every cache receiving the event. If "immediate" means zero-window revocation
is mandatory, use opaque reference tokens with introspection at an edge
authorizer, or route all protected traffic through a centralized authorizer
that maintains the revocation state. This is a deliberate latency/availability
trade-off; stateless JWTs alone cannot meet that requirement.

For GDPR deletion, Identity should synchronously mark the account disabled in
the authoritative identity store, revoke refresh tokens, publish the
deactivation event, and require downstream services to reject commands for
the deleted subject even if their local data-cleanup event is still pending.
Deletion workflows then remove personal data asynchronously, while the
authorization block takes effect through the revocation propagation path.

Do not use an unbounded per-request blacklist. Prefer session-version
invalidation for bulk logout/account deletion and reserve `jti` entries for
specific early revocations. Protect revocation topics and caches with service
authentication, replay-safe event IDs, monitoring, and reconciliation against
Identity so a lost or delayed event is detected.

### Resulting correction

Proposals 2 and 3 should describe real-time delivery as a connection service
plus durable notification store, not as a domain service directly pushing to
an arbitrary application node. They should describe JWT authorization as
local cryptographic validation plus replicated revocation/account state, not
as revocation through JWT expiry alone. Zero-window revocation requires
central introspection or opaque tokens and must be selected explicitly.
