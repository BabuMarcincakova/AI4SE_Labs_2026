---
name: architectural-review-and-adr
description: "Use when analyzing software requirements, proposing and comparing architectures, probing low-level failure modes, selecting an architecture, and producing or refining an Architecture Decision Record (ADR)."
argument-hint: "[requirements file or system to review]"
---

# Architectural Review and ADR

## What this skill does

Run a requirements-grounded architecture review that compares three distinct
architectural options, explores implementation failure modes, records the
discussion, selects an option, and creates or refines an ADR.

Keep system-specific facts in the review log, ADR, and
`./references/onesport-examples.md` only when working on OneSport. This skill
itself must remain system-agnostic.

## Workflow

### 1. Read and normalize requirements

1. Locate and read the complete requirements source.
2. Summarize only stated goals, user capabilities, constraints, and explicit
   non-functional requirements.
3. Separate stated requirements from inferred constraints and unresolved gaps.
4. Ask clarifying questions when a decision materially changes the design.
5. Establish a running engineering log. Record synthesized decisions and
   questions, not a verbatim transcript.

### 2. Establish evaluation criteria

Use criteria grounded in the requirements, including:

- Operational complexity
- Transactional consistency and concurrency
- Infrastructure and cost at the expected scale
- Time-to-market and development velocity
- Privacy/compliance implications
- Availability, failure isolation, and scaling needs
- Ease of testing, debugging, and migration

Do not invent scale, SLOs, providers, regulations, or product behavior. Mark
missing information as an open decision or gap.

### 3. Propose three genuinely distinct architectures

Present the options one at a time when the discussion requires staged review.
For each option document:

- High-level component shape and responsibilities
- State ownership and data model implications
- Synchronous versus asynchronous communication
- Why it fits the requirements
- Benefits and trade-offs
- Low-level implementation pain points
- Scaling and operational model
- Conditions under which it is or is not suitable

The three reusable candidate styles from the source review are:

1. **Modular monolith with a relational core**
2. **Event-driven microservices with database-per-service**
3. **Serverless application with managed state and workflows**

Use these as candidate patterns, not mandatory answers. If another option is
needed, explain why it is a distinct replacement.

### 4. Conduct failure-mode probing

After each relevant proposal, use
`./references/probing-checklist.md`. Follow the most consequential risks
through concrete execution timelines, transaction boundaries, retries, locks,
timeouts, and recovery behavior.

Require explicit treatment of:

- Race conditions and duplicate operations
- Database capacity and connection isolation
- Message delivery, outbox publishing, retries, ordering, and replay
- Privacy deletion and retention across all data stores
- Real-time connection ownership and reconnect behavior
- Authentication, authorization, logout, and revocation
- Partial failures and truthful user experience

Do not claim exactly-once behavior without explaining the boundary that
provides it. Prefer durable state, idempotency, explicit status, bounded
retries, and reconciliation.

### 5. Select and justify a decision

Compare all options in an executive table using the agreed criteria. State:

- Selected architecture
- Scope and status of the decision
- Why it wins under the known requirements
- Why the alternatives were not selected now
- Conditions that would trigger reconsideration

If requirements are insufficient for a responsible selection, ask for the
missing decision rather than presenting a false certainty.

### 6. Create the ADR

Use `./references/adr-template.md`. Include:

- Title, status, date, owners, and scope
- Executive comparison table
- Context and decision drivers
- Considered options
- Decision and architecture diagram
- Low-level implementation strategy
- Consequences, risks, mitigations, and open decisions

Keep the ADR formal and durable. Put conversational feedback in the separate
discussion log.

### 7. Iterate and maintain records

1. Create a separate discussion log for the ADR task.
2. Present the initial ADR for review.
3. Record feedback as a concise engineering decision.
4. Revise the ADR surgically.
5. Verify the final status and that the log and ADR agree.
6. Do not run a trial implementation unless the user asks for one.

## Output discipline

- Never put system-specific examples in this file.
- Link or reference companion files with relative paths.
- Distinguish facts, decisions, assumptions, risks, and gaps.
- Preserve unresolved questions instead of silently filling them in.
- Use diagrams and tables where they clarify comparison or data flow.
