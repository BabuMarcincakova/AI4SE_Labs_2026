# ADR-NNN: [Decision title]

- **Status:** Proposed | Accepted | Superseded | Rejected
- **Date:** [YYYY-MM-DD]
- **Decision owners:** [team or owners]
- **Scope:** [system or decision scope]
- **Related records:** [links]

## Executive summary

| Option | Operational complexity | Transactional consistency & concurrency | Infrastructure & cost at expected scale | Time-to-market / development velocity | Assessment |
|---|---|---|---|---|---|
| Option 1 | [summary] | [summary] | [summary] | [summary] | [assessment] |
| Option 2 | [summary] | [summary] | [summary] | [summary] | [assessment] |
| Option 3 | [summary] | [summary] | [summary] | [summary] | [assessment] |

## Context

[State the requirements, system goals, known scale, explicit constraints, and
important exclusions. Separate facts from assumptions and list gaps.]

## Decision drivers

1. [driver]
2. [driver]
3. [driver]

## Considered options

### Option 1: [name]

[Shape, responsibilities, data ownership, communication model, strengths,
weaknesses, and suitability.]

### Option 2: [name]

[Shape, responsibilities, data ownership, communication model, strengths,
weaknesses, and suitability.]

### Option 3: [name]

[Shape, responsibilities, data ownership, communication model, strengths,
weaknesses, and suitability.]

## Decision

Select **[option]** for [scope].

[Explain why it wins now, why the alternatives are deferred or rejected, and
what would trigger reconsideration.]

### Selected architecture

```text
[ASCII/text-based architecture diagram]
```

## Architecture details

### Boundaries and data ownership

[Modules/services, schema or database ownership, API boundaries, and
enforcement mechanisms.]

### Consistency and concurrency

[Transaction isolation, locks, ordering, unique constraints, idempotency,
state transitions, and overload behavior.]

### Communication and workers

[Synchronous/asynchronous boundaries, outbox or equivalent, retries, message
delivery, worker isolation, pools, backpressure, and reconciliation.]

### Privacy and account lifecycle

[Revocation, deletion/anonymization, relationships, audit evidence, stores,
retention, backups, and verification.]

### Authentication, authorization, and real time

[Credential/session model, token revocation, connection ownership, presence,
live delivery, durable replay, and partial failure behavior.]

## Consequences

### Positive consequences

- [benefit]

### Negative consequences

- [cost or risk]

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| [risk] | [mitigation] |

## Implementation strategy

### Phase 1: Foundations

- [step]

### Phase 2: Core product

- [step]

### Phase 3: Resilience, privacy, and operations

- [step]

### Phase 4: Evidence-based scaling

- [measurement, threshold, or extraction step]

## Open decisions and acceptance criteria

- [open decision]
- [acceptance criterion]
