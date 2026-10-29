# Skill Comparison Report

## Evidence and provenance

This comparison uses both complete record sets: the original Task 1 review,
Task 2 discussion log and ADR, and the new run's Task 1 review, discussion log
and ADR. The new-run agent was explicitly instructed **not to read the original
OneSport files**. It was told to work only from the supplied requirements, the
skill, and its references.

- Verification of actual behaviour (from the chat tool-call history):
  Agent did not open any original OneSport file. I checked during the process files it read
- Same model and same requirements text in both runs:
   Same model was used: gpt-5.6 luna

## Effort

Exact conversation-turn and prompt counts cannot be derived from the records.
Both discussion logs identify themselves as synthesized rather than verbatim
transcripts. The original records document feedback and acceptance. The new run
paused after Task 1 as instructed and then completed Task 2.

User-reported estimates (not taken from the logs):

| Metric | Original run | Skill run |
|---|---|---|
| Prompts I typed | 7 | 3 |
| Clarification questions answered | 8 | 4 |
| Elapsed time (approx.) | 10 min. | 4 min. |

(Prompts and questions were from conversation, elapsed time is only how long executing prompts took. I did not count time I spent reading)

## Coverage and probing

Both runs compared a modular monolith, event-driven microservices, and a
serverless architecture. Both covered concurrency, idempotency, outbox
publication, retries, deletion, realtime connection ownership and reconnect,
authentication revocation, and partial failures.

The original run has deeper concrete probing of outbox publisher failure, GDPR
erasure across service databases, BFF partial-failure semantics, serverless
database bottlenecks and retry storms, scaling beyond one relational write
authority, realtime routing, and zero-window JWT revocation. The skill-guided
run is stronger at explicitly separating requirements, assumptions, and gaps.

The original review was built over several round of my questions and feedback.

## ADR quality

Both ADRs are structurally complete and consistent: each is Accepted, selects
the modular monolith with a relational core, compares all three options, and
includes a diagram, decision drivers, boundaries, concurrency, outbox and
workers, deletion, authentication and realtime, consequences, risks,
implementation phases, and open decisions. The new ADR follows the supplied
template more visibly and adds explicit acceptance criteria. The original ADR
contains more detailed implementation treatment in some areas, especially
capacity and revocation. Each log agrees with its own decision.

## Where the skill helped or introduced problems

The skill improved consistency by requiring normalized requirements,
evaluation criteria, three distinct options, explicit gaps, failure-mode
probes, and a durable ADR structure.

## Skill improvements

The checklist is not complete. The original run caught probes that it lacks
explicitly:

- BFF/API composition semantics: distinguish confirmed empty data from
  unavailable upstream data in the user response.
- Provider-data correctness: external identity changes, timezone handling,
  normalization, deduplication, stale-record policy, and licensing.
- Non-idempotent external provider calls: decide how a timeout after an unknown
  commit is reconciled before retrying.
- Read-versus-write scaling: prefer measured read scaling and do not split
  write ownership merely to claim horizontal scaling.
- Serverless-specific admission control tied to database capacity, and an
  explicit "distributed monolith" failure mode.