# OneSport Task 1: Architecture Review

## Review scope

This review is grounded in the supplied OneSport requirements and the
architectural-review workflow. It compares three genuinely different
architectures and probes their most consequential implementation failure modes.
The formal ADR is intentionally deferred to Task 2.

## Requirements normalization

### Stated capabilities

- Users can sign up, log in, log out, view and edit profile credentials, and
  delete their accounts.
- Users can browse recent sports news and upcoming sporting-event tickets,
  filtering both by country.
- Authenticated users can save and remove news and tickets, clear both
  collections, and view their saved items.
- Users can send, accept, refuse, and delete friend relationships, find a user
  by email, and view friends' details.

### Stated constraints and non-functional requirements

The source requirements do not state a traffic volume, availability target,
latency target, content freshness SLA, deployment provider, budget, regulatory
jurisdiction, or team size.

### Documented assumptions

The following answers were confirmed before the proposals were prepared:

1. No scale or SLO is specified. The design must therefore avoid claiming
   scale-specific guarantees.
2. OneSport discovers and displays ticket availability and lets users save
   tickets for later; payment and checkout are performed by an external
   provider.
3. Current content is desirable, but no real-time delivery SLA is specified.
4. Account deletion follows a least-retention, verifiable deletion or
   anonymization policy.

### Unresolved gaps

- Expected peak concurrency and geographic distribution.
- News and ticket data providers, rate limits, licenses, and outage contracts.
- Whether friend updates require live delivery or ordinary refresh is enough.
- Exact country list, filtering semantics, and handling of incomplete provider
  data.
- Whether moderation, audit, administrator access, or abuse reporting is in
  scope.
- Required recovery point and recovery time objectives.

## Evaluation criteria

The proposals are compared using operational complexity, transactional
consistency and concurrency, infrastructure and cost at the unspecified
expected scale, time-to-market, privacy implications, availability and failure
isolation, and ease of testing, debugging, and migration.

## Option 1: Modular monolith with a relational core

### Shape and responsibilities

One deployable application contains strict modules for Identity, Content,
Ticket Catalog, Collections, Social, and Notifications/Admin if needed. A
relational database is the authoritative store. External provider adapters
ingest news and ticket data through bounded workers. A transactional outbox
records events for notifications and integration work.

Requests are synchronous for login, browsing, saving, and friend mutations.
Provider ingestion, notification delivery, deletion cleanup, and retries are
asynchronous. Modules communicate through explicit application interfaces,
not direct access to one another's tables.

### State ownership and data model

Identity owns accounts, credential versions, sessions, and deletion state.
Content owns canonical news items and provider metadata. Catalog owns events,
ticket availability, and freshness status. Collections owns saved-news and
saved-ticket rows. Social owns directed requests and canonical undirected
friendship pairs. A relational schema can enforce unique collection entries,
one pending request per directed pair, and one friendship per normalized pair.

### Benefits and trade-offs

This is the fastest option to build and test while preserving transactions
across closely related user operations. It has one operational surface and
supports a later extraction path. Its risks are shared-database coupling,
coordinated deploys, and the need to prevent module boundaries from becoming
nominal only.

### Low-level pain points

- Friend requests need deterministic locking of the two user identities,
  re-reading state after locks, and unique constraints to prevent reciprocal
  races.
- Save operations need idempotent `(user_id, item_id)` keys because clients
  may retry after a lost response.
- Provider data needs explicit `unknown`, `stale`, and `unavailable` states
  rather than treating an empty result as confirmed absence.
- Outbox relays publish at least once; consumers must deduplicate by event ID.
- Worker connection pools and concurrency must be isolated from interactive
  requests.

### Failure-mode probe

If two users send reciprocal friend requests concurrently, both requests first
normalize the pair and lock the two user rows in the same order under a
relational transaction. Each re-reads pending requests and friendship state.
The second transaction waits, then observes the first commit and applies the
defined reciprocal-request policy. A unique normalized friendship key and a
directed pending-request constraint make duplicate state impossible.

If a save transaction commits but the HTTP response is lost, the retry sees
the unique key and returns the existing saved state. If state and an event
must change together, the outbox row commits in the same transaction. A relay
lease recovers crashed publishers; broker acknowledgement precedes marking
published; repeated failures move to dead letter and trigger reconciliation.

Account deletion immediately disables login and revokes sessions. An
idempotent workflow removes or anonymizes credentials, profile data,
collections, notification destinations, and personal references in outbox
and worker stores. Shared news and event records remain without unnecessary
personal data. Deletion progress is durable and verifiable; immutable backup
expiry remains an open policy decision.

If a realtime gateway is later introduced, it owns connections and presence,
while durable notification rows remain the replay source. Reconnect uses a
cursor, not a promise that a live socket is durable. Authentication uses
short-lived access credentials and rotating refresh credentials; account
version changes invalidate all sessions. Exact zero-window revocation would
require centralized introspection and is not assumed here.

### Suitability

Best fit when the team needs a coherent first release and the missing scale
and SLO information does not justify distributed operational complexity.
Reconsider if independent scaling, team ownership, or fault isolation becomes
an evidenced bottleneck.

## Option 2: Event-driven microservices with database per service

### Shape and responsibilities

Identity, Content, Catalog, Collections, Social, and Notifications are
independently deployed services. Each owns a database and exposes APIs or
versioned events. An API gateway or BFF composes browsing responses. Provider
adapters and notification workers consume broker topics.

Interactive mutations are synchronous within one service. Cross-service
effects are asynchronous through an outbox and broker. A saga or explicit
workflow coordinates operations that cross ownership boundaries; no
distributed transaction is assumed.

### State ownership and data model

Each service owns its schema and publishes stable identifiers and events.
Collections stores references to content and catalog IDs, not copied
authoritative records. Read models in the BFF or a query service denormalize
data for combined screens. Search-by-email must be authorized and mediated by
Identity rather than implemented as an unrestricted cross-service query.

### Benefits and trade-offs

Services can scale and fail independently, and ownership boundaries are
strong. Provider ingestion or realtime delivery can be isolated from login
traffic. The cost is substantially higher deployment, observability, schema
compatibility, local-development, and incident-response complexity. Eventual
consistency becomes visible to users.

### Low-level pain points

- A saved ticket may reference a catalog item whose projection is stale or
  deleted; the read model must distinguish missing, stale, and unavailable.
- Broker delivery is at least once and possibly out of order. Consumers need
  event IDs, aggregate versions, idempotency tables, and replay procedures.
- Account deletion is a distributed workflow spanning databases, queues,
  caches, search indexes, logs, and backups; completion must be tracked.
- BFF composition can turn one partial service failure into a misleading
  empty page unless errors are represented separately from empty collections.
- Per-service pools and retry budgets are mandatory to avoid cascading
  overload.

### Failure-mode probe

A Social service commit followed by a broker outage leaves the outbox as the
durable publication obligation. Lease expiry and backoff recover publisher
crashes; consumers deduplicate and reject older aggregate versions. A
poison event goes to a dead-letter stream with an operator-visible
reconciliation path. There is no exactly-once end-to-end behavior.

During deletion, Identity revokes access first, then emits a deletion
workflow with a stable request ID. Each service handles it idempotently and
reports completion. A coordinator retries boundedly and escalates incomplete
stores. Until completion, access remains denied. Backups and immutable logs
require explicit retention and minimization rules.

For realtime updates, a notification event addresses a user ID, not a
container. A presence registry maps user, connection, node, and lease expiry.
The router can deliver to multiple devices; persisted notifications support
cursor replay after reconnect. Loss of the router must degrade to delayed
delivery, not falsely report successful live delivery.

### Suitability

Suitable when measured scale, organizational ownership, or fault isolation
requires independent services. It is premature without those drivers because
the requirements do not establish them and the consistency/debugging burden
is high.

## Option 3: Serverless application with managed state and workflows

### Shape and responsibilities

An API gateway invokes stateless functions for identity, content, catalog,
collections, and social operations. Managed relational or document storage,
queues, scheduled jobs, event buses, and workflow orchestration provide
durability. Provider ingestion runs as scheduled or event-triggered
functions. A managed realtime service is used only if live updates become a
confirmed requirement.

Requests are short synchronous function calls. Long-running deletion,
provider refresh, notification, and reconciliation work is asynchronous in
durable workflows and queues.

### State ownership and data model

Functions are organized by bounded context, but state lives in managed
datastores. Relational storage is preferable for account, collection, and
friendship invariants; a document or key-value store may serve provider
projections. Idempotency records, workflow state, and dead-letter messages
are first-class durable data.

### Benefits and trade-offs

This minimizes server management and can scale bursts automatically. It
shortens the path to scheduled ingestion and managed retry workflows. Costs
can be attractive at low or irregular traffic, but provider and platform
coupling, cold starts, execution limits, local testing, distributed tracing,
and database connection pressure are significant risks.

### Low-level pain points

- Automatic function concurrency can exhaust database connections or provider
  quotas; admission control and bounded concurrency are required.
- Retries can duplicate friend requests, saves, provider calls, and
  notifications. Every mutation needs an idempotency key and a durable
  result or state transition.
- Workflow steps can time out after committing. Recovery must query durable
  state rather than assume the step did not run.
- A managed realtime gateway still needs presence leases, replay cursors, and
  authorization; serverless execution does not remove connection ownership.
- Cold-start and platform-specific behavior complicate deterministic tests and
  migration to another runtime.

### Failure-mode probe

If a function commits a save and times out before responding, the idempotency
record lets the retry return the committed result. If a provider call times
out, the system must not blindly retry a non-idempotent external operation;
it needs provider idempotency support or a pending state and reconciliation
job. Queue delivery is at least once, so handlers use stable event IDs.

If database capacity is reached, admission control rejects or delays work
with a truthful retryable response; jittered retries and a dead-letter queue
prevent a retry storm. Interactive capacity is reserved separately from
refresh workers. Deletion is a durable workflow with per-store checkpoints,
idempotent handlers, immediate revocation, and an auditable completion state.

### Suitability

Suitable when the organization already standardizes on managed serverless
services, traffic is bursty, and platform limits are acceptable. It is less
attractive when the product requires complex relational transactions,
predictable local debugging, or provider portability.

## Cross-option comparison

| Criterion | Modular monolith | Event-driven microservices | Serverless workflows |
|---|---|---|---|
| Operational complexity | Lowest; one deployable system plus workers | Highest; many services, broker, and read models | Medium; low server ops but high platform complexity |
| Consistency and concurrency | Strong local transactions and constraints | Local consistency; cross-service eventual consistency | Strong only within bounded transactions; workflow consistency elsewhere |
| Cost at unspecified scale | Predictable baseline; scale vertically/horizontally | Higher fixed operational and observability cost | Potentially efficient for bursty/low use; platform costs can surprise |
| Development velocity | Fastest initial delivery and simplest tests | Slowest due to contracts and distributed debugging | Fast for managed integrations, slower for deep testing |
| Privacy/deletion | One coordinated workflow and fewer copies | Most difficult across stores and projections | Workflow-friendly but platform logs/backups need careful controls |
| Availability and isolation | Shared process/database failure domain | Strongest independent isolation | Managed scaling, but quota/provider coupling |
| Migration/testing | Clear extraction path; easy local integration tests | Strong boundaries but expensive migration and replay testing | Portable only with discipline; emulator gaps are a risk |
| Overall assessment now | **Preferred starting point** | Defer pending measured drivers | Viable alternative pending platform constraints |

## Provisional recommendation for Task 2

Select the modular monolith with a relational core as the initial direction,
subject to confirmation of scale, SLO, provider, and compliance gaps. It
provides the strongest transactional foundation for collections and
friendships, keeps account deletion tractable, and avoids paying the
microservice or serverless complexity tax before the requirements justify it.
The ADR should record extraction triggers such as sustained database
contention, independently scaling provider ingestion, or a team boundary that
requires service isolation.

