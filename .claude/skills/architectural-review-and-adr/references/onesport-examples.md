# OneSport-Specific Examples

These examples are extracted from the OneSport Task 1 and Task 2 records.
They are deliberately kept out of `SKILL.md` so the workflow remains
system-agnostic.

## Selected architecture

The accepted initial decision is a modular monolith with PostgreSQL, strict
Identity, Catalog, Collections, Social, Notifications, and Admin modules, plus
separate bounded availability and notification workers.

## Concurrency locking

For friend requests:

1. Compute `user_low_id = min(user_a, user_b)` and
   `user_high_id = max(user_a, user_b)`.
2. Use PostgreSQL `READ COMMITTED`.
3. Lock both user rows in ascending order with `SELECT ... FOR UPDATE`.
4. Re-read friendship and pending-request state after the locks are acquired.
5. Apply the reciprocal-request policy.
6. Transition the request and insert the canonical friendship atomically.

The friendship key uses `(user_low_id, user_high_id)` with
`CHECK (user_low_id < user_high_id)`. A partial unique index prevents more than
one pending request per directed pair. Saved tickets use a unique
`(user_id, ticket_id)` key.

## Transactional outbox relay

When a module changes state and emits an event:

1. Commit the state change and outbox row in one transaction.
2. Relay rows using a lease.
3. Publish with a stable event ID.
4. Mark the row published only after broker acknowledgement.
5. Recover expired publishing leases.
6. Retry with backoff and move repeatedly failing rows to dead letter.

Duplicate publication is accepted; consumers deduplicate by event ID.

## GDPR erasure

OneSport uses a hybrid strategy:

- Disable login and revoke sessions immediately.
- Keep a non-identifying deletion tombstone when referential integrity needs
  it.
- Remove or irreversibly anonymize email, password hashes, profile fields,
  tokens, and notification destinations.
- Hard-delete saved-news, saved-ticket, notification, and preference rows.
- Remove or transition friendships and pending requests to preserve the other
  user's usable data.
- Preserve shared news, events, and ticket records.
- Retain only minimized, explicitly justified audit evidence.
- Run an idempotent bounded workflow and verify that personal references are
  gone.

## WebSocket/SSE presence routing

Domain services publish a notification containing a user ID and event ID, not
a node address. A realtime gateway records:

```text
(user_id, connection_id, node_id, expires_at)
```

The presence record uses a lease or heartbeat. A notification router publishes
to a user or partition channel, and the gateway node holding the connection
delivers it. Multiple devices and tabs are supported. Notifications are
persisted before live delivery, and reconnecting clients replay missed events
using a cursor or last-seen event ID.

## JWT versioning and revocation

OneSport uses short-lived access JWTs with rotating refresh tokens. Tokens
contain a subject, `jti`, issued-at time, expiry, and session/account version.
Identity publishes durable revocation events. Downstream components verify
signatures locally and consult replicated account-status and revocation state.

Session/account-version invalidation handles bulk logout or deletion;
individual `jti` entries handle targeted early revocation. Protected mutations
fail closed when revocation state is unavailable or too stale. A zero-window
guarantee would require opaque reference tokens or centralized introspection.

## Other extracted examples

- Ticket availability is authoritative in Catalog, with `unknown` kept
  distinct from `unavailable`.
- Availability workers use bounded batches, separate pools, queue backpressure,
  and short transactions.
- BFF partial failures distinguish confirmed empty data (`items: []`) from
  unavailable data (`items: null` with an error status).
- Serverless database capacity is protected with bounded function concurrency,
  admission control, jittered retries, idempotency keys, and dead-letter
  handling.
