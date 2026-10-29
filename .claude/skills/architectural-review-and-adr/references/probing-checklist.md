# Architecture Failure-Mode Probing Checklist

Use these questions after proposing an architecture. Adapt nouns to the
system under review and record answers, assumptions, and unresolved gaps.

## Concurrency and transactions

- What happens if two users perform the same operation at the same time?
- What is the exact transaction boundary?
- Which isolation level is used, and why?
- Which rows, keys, or logical aggregates are locked?
- Are locks acquired in a deterministic order to avoid deadlocks?
- Which unique constraints make duplicate state impossible?
- What does the second concurrent request observe after waiting for a lock?
- Is a retry safe if the first attempt committed but the response was lost?
- How are hot keys, lock waits, deadlocks, and overload surfaced?
- What is the behavior for duplicate, reversed, cancelled, or already-completed
  state transitions?

## Consistency, messaging, and workers

- Which data is authoritative, and which data is a projection or cache?
- Which interactions are synchronous, and which are asynchronous?
- If state commits but event publication fails, where is the durable obligation?
- How are publisher crashes, expired leases, retries, and dead letters handled?
- What delivery guarantee is used: at-most-once, at-least-once, or another
  explicitly defined guarantee?
- How are duplicate and out-of-order messages detected?
- How are event contracts versioned without breaking older consumers?
- Which component owns retries, and how are retry storms prevented?
- How are worker connection pools, concurrency, batches, and backpressure
  isolated from interactive traffic?
- How are stale projections, failed consumers, and reconciliation detected?

## Privacy and compliance

- What data is personal, sensitive, shared, derived, or operational?
- What happens immediately when an account or subject is deleted?
- Which stores contain copies, projections, caches, logs, traces, queues,
  archives, and backups?
- How is access revoked before asynchronous erasure completes?
- Is deletion hard delete, anonymization, tombstoning, or a documented hybrid?
- How are relationships to other users preserved without retaining unnecessary
  personal data?
- What retention exceptions are legitimate, minimized, and access-controlled?
- How is erasure progress tracked, verified, reported, and escalated before a
  legal deadline?
- Are deletion commands and handlers idempotent?
- What is the policy for immutable backups and their expiry?

## Real-time delivery

- Which component owns live connections?
- How does a domain event find all active connections for a subject without
  knowing a server or container address?
- How are presence, leases, heartbeats, disconnects, and crashed nodes handled?
- Can a subject have multiple devices, tabs, or simultaneous connections?
- Is live delivery durable, or is durable notification storage separate?
- How do clients reconnect and replay missed events?
- How are duplicate live messages deduplicated?
- What happens when the connection gateway, broker, or notification worker is
  unavailable?
- Does the design rely on sticky sessions for correctness?

## Authentication and authorization

- Where is authentication verified, and where is authorization enforced?
- Can every protected operation derive the acting subject from trusted
  credentials rather than client-supplied identifiers?
- How do logout, credential change, account disablement, and deletion revoke
  existing sessions or tokens?
- If tokens are locally verified, how does revocation reach verifiers without a
  synchronous identity call on every request?
- What is the maximum revocation propagation window?
- What happens if revocation state is stale or unavailable?
- Are access tokens short-lived and refresh tokens rotated?
- Are token identifiers, session versions, or account versions used for
  targeted or bulk invalidation?
- Do service-to-service calls have independent authentication and authorization?
- Are denial paths, IDOR attempts, and confused-deputy risks tested?
