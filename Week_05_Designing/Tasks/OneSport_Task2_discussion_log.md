# OneSport Task 2 ADR Discussion Log

## Purpose

This is the separate Task 2 engineering log. It records the ADR creation,
feedback, decisions, and revisions as a synthesized review record. Task 1
discussion notes remain in
[OneSport_architecture_review_Task1.md](./OneSport_architecture_review_Task1.md)
and are not modified by this Task 2 log.

## 2026-10-29 - Initial ADR request

### User request summary

The user asked to begin Task 2 by reading the completed Task 1 architecture
review, selecting the final architecture, creating a formal ADR in a new
`OneSport_ADR.md` file, and maintaining this separate discussion log. The
initial ADR must include:

- Standard ADR sections
- A comparison table for all three proposals
- A text-based architecture diagram
- Concurrency controls and database constraints
- Transactional outbox and connection-pooling details
- GDPR erasure strategy
- Real-time socket routing
- JWT revocation

The user also requested an iterative review process: present the initial ADR,
ask for feedback, and refine the document in subsequent turns.

### Initial decision recorded

Task 1 did not contain a separate final-selection statement, so this initial
ADR records the recommendation supported by its trade-off analysis:

> Select Proposal 1, the modular monolith with PostgreSQL, as the initial
> production architecture.

This is a reviewable initial decision, not a claim that Proposals 2 or 3 are
invalid. Proposal 2 remains an extraction path if independently scalable
domains or multiple autonomous teams become necessary. Proposal 3 remains an
option for selected bursty workloads if cloud-first operations justify its
vendor coupling.

### Why Proposal 1 is the initial recommendation

- OneSport has tens of thousands of expected users, not an established need
  for distributed service deployment.
- Social relationships, saved collections, account deletion, and identity
  require strong transactional integrity.
- News, event, and ticket data are administered internally.
- A separate worker and notification subsystem can isolate availability
  monitoring without making the whole product distributed.
- A relational database provides constraints and pair-locking for the hardest
  consistency problems.
- The architecture can scale reads, workers, and selected domains before
  considering service extraction.

### Review status

Initial versions of
[OneSport_ADR.md](./OneSport_ADR.md) and this discussion log have been
created. The user is invited to review structure, depth, decision framing,
diagram clarity, and whether any implementation detail is missing.

## 2026-10-29 - First ADR feedback

The user confirmed that Proposal 1 should remain selected and requested a
clearer executive comparison of all three options across:

1. Operational complexity
2. Transactional consistency and concurrency
3. Infrastructure and cost for tens of thousands of users
4. Time-to-market and development velocity

The ADR executive summary table was revised to use these four dimensions
directly. The assessment remains that Proposal 1 offers the best initial
balance for OneSport, while Proposal 2 and Proposal 3 retain conditional
advantages for independently scaling or bursty workloads.

## 2026-10-29 - ADR acceptance

The user approved the reviewed architecture decision and requested the ADR
status be changed from `Proposed for review` to `Accepted`. The ADR now
formally selects the modular monolith with PostgreSQL as OneSport's initial
production architecture.
