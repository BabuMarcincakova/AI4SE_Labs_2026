# OneSport Task 1 Discussion Log

## Purpose

This is a synthesized engineering log rather than a verbatim transcript. It
records the questions asked, the answers received, assumptions made, and
decisions reached while preparing the Task 1 architecture review. The log was
started before proposing architectures as required by the workflow.

## Questions asked

### 1. What scale and availability target should drive the comparison?

**Answer:** No scale or SLO is specified; use a documented assumption.

**Recorded implication:** The review must not claim a capacity, latency, or
availability guarantee. It compares baseline operational cost and identifies
scale-triggered reconsideration conditions.

### 2. Does OneSport own ticket checkout and payment?

**Answer:** Use the documented assumption that OneSport provides discovery,
availability, and saving, while purchase occurs through an external provider.

**Recorded implication:** Payment, order state, refunds, and card-data handling
are outside this review. Provider links, availability freshness, outages, and
rate limits remain architectural concerns.

### 3. Is real-time delivery required?

**Answer:** Current content is desirable, but no real-time SLA is specified;
use a documented assumption.

**Recorded implication:** The proposals support asynchronous refresh and
truthful stale/unavailable states. Realtime connections are treated as an
optional later capability, with durable notifications and replay required if
introduced.

### 4. What deletion and privacy policy applies?

**Answer:** Use a least-retention, verifiable deletion or anonymization policy.

**Recorded implication:** Login access is revoked immediately. Personal
credentials, profile data, collections, destinations, and unnecessary
references are removed or anonymized through an idempotent workflow. Backup
retention and jurisdiction-specific deadlines remain open decisions.

## Synthesized architecture discussion

### Decision reached: compare three distinct options

The review compares:

1. A modular monolith with a relational core.
2. Event-driven microservices with database-per-service.
3. A serverless application with managed state and workflows.

They are distinct in deployment topology, state ownership, consistency
boundaries, and operational model rather than merely different labels for the
same design.

### Decision reached: preserve explicit facts, assumptions, and gaps

The requirements establish user capabilities but do not establish scale,
providers, SLOs, freshness, regulation, or administration. These are kept as
gaps instead of being presented as facts. External ticket purchasing and
least-retention deletion are recorded as confirmed working assumptions.

### Decision reached: probe failure modes, not only component diagrams

Each option was tested against concurrent friend requests and duplicate
saves, commit-versus-publication failure, retries and replay, deletion across
copies, realtime reconnects, and authentication revocation. No option claims
end-to-end exactly-once behavior.

### Provisional decision for Task 2

The modular monolith with a relational core is the preferred initial
architecture because it gives the user-facing account, collection, and social
operations strong local transactions with the lowest operational burden. It
must enforce module boundaries, use an outbox for asynchronous effects, isolate
workers, and retain an extraction path.

This is provisional until the Task 2 ADR is reviewed. Microservices should be
reconsidered when measured scale, independent ownership, or fault-isolation
needs justify the distributed consistency and operations cost. Serverless
should be reconsidered when managed-platform standardization, bursty traffic,
and its execution/database limits are acceptable.

## Open decisions carried forward

- Peak concurrency, geographic distribution, and recovery objectives.
- News and ticket provider contracts, quotas, licenses, and freshness.
- Whether friend and notification updates need live delivery.
- Country/filter semantics and handling of incomplete provider data.
- Moderation, admin, abuse prevention, and audit scope.
- Backup retention, deletion deadlines, and applicable jurisdiction.

## Task 2: ADR decision and review log

The Task 1 review was accepted as the basis for the ADR after the user
confirmed that Task 1 looked good and instructed the work to proceed. This
section records the ADR questions, answers, and decisions as synthesized
engineering notes rather than a verbatim transcript.

### Question 1: Which architecture should be selected?

**Answer:** Select the modular monolith with a relational core for the
initial OneSport production system.

**Decision:** The architecture is accepted for the initial scope. It gives
identity, saved collections, and social operations strong local transactions
with lower operational complexity. The outbox and bounded workers provide
asynchronous provider and notification processing without distributing every
domain.

### Question 2: Is the ADR informative enough for implementation?

**Answer:** It must include more than a high-level choice. The ADR includes
the comparison table, context and assumptions, all three options, a selected
architecture diagram, module/data ownership, concurrency controls, outbox
delivery, worker isolation, deletion, authentication, realtime behavior,
consequences, risks, implementation phases, and acceptance criteria.

**Decision:** Use the ADR template structure and preserve the distinction
between requirements, confirmed assumptions, risks, and open decisions.

### Question 3: What concrete correctness boundaries must the ADR record?

**Answer:** Friend operations need deterministic pair locking and canonical
friendship uniqueness. Collection operations need idempotent unique keys.
State and event publication need a transactional outbox. At-least-once
delivery requires stable event IDs and deduplicating consumers.

**Decision:** The ADR explicitly rejects an end-to-end exactly-once claim and
defines leases, retries, dead letters, replay, and reconciliation.

### Question 4: How should deletion, authentication, and realtime behavior be
represented?

**Answer:** Revoke access first, then execute an idempotent, verifiable
deletion workflow across personal-data stores. Use short-lived access JWTs,
rotating refresh tokens, account/session versions, and replicated revocation
state. If realtime delivery is introduced, persist notifications before live
delivery and replay by cursor after reconnect.

**Decision:** These are included as architecture details, with the
zero-window JWT revocation limitation and backup-retention policy retained as
explicit open decisions.

### ADR self-review and revision decisions

The first ADR structure was checked against the skill template. The final
record retains the executive comparison table and adds a text architecture
diagram, explicit option suitability, implementation phases, measurable
scaling evidence, risk mitigations, and acceptance criteria. No unsupported
traffic, availability, provider, or regulatory facts were added. The ADR
status is **Accepted** for the initial architecture, while unresolved
requirements remain open and are not treated as design guarantees.

### Final Task 2 decision

The accepted decision is **a modular monolith with a relational core,
separate bounded workers, and an outbox-based asynchronous boundary**.
Microservices and serverless remain valid future alternatives only when
measured scale, independent ownership, platform constraints, or failure
isolation provide a documented reason to reconsider the decision.
