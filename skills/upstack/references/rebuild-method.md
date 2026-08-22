# Rebuild and Reverse-Engineering Method

Use this reference for `/upstack reverse`, `/upstack blueprint`, `/upstack build`, and `/upstack stage`.

## Two workflows, one evidence loop

Upstack supports both understanding an existing project and rebuilding a selected project. Do not make the learner read or implement the whole system at once.

| Workflow | Question | First artifact |
| --- | --- | --- |
| Reverse engineer | Can the learner explain how one real flow works and make a safe change? | Source-grounded trace |
| Build apprentice | Can the learner recreate one externally observable behavior from a recipe? | Staged blueprint |

The shared loop is:

```text
orient → choose a slice → state the hypothesis → inspect sources
→ predict the next hop → implement or trace → verify → explain → reflect
```

## Stage recipe

A stage is complete only when it has an observable outcome and evidence. Use the following shape:

```markdown
# Stage 003 — First authenticated request

## Outcome
The learner can implement and explain one authenticated request path.

## Focus
- Surface: backend API
- Entry point: `src/routes/session.ts`
- Concepts: HTTP routing, middleware, token validation, persistence
- Provenance: observed source anchors from the selected reference repository

## Learner decisions
- What should happen for missing, malformed, expired, and valid credentials?
- Which public seam should the test observe?

## Task
Implement the smallest vertical slice. Do not copy the reference implementation.

## Approved checks
- documented unit test command
- targeted integration fixture, after confirmation

## Proof questions
- Explain where the request enters and where identity becomes available.
- Explain one security trade-off and one limitation.

## Finish gates
- normal request works;
- invalid and boundary cases are considered;
- learner can explain the flow without opening the solution.

## Next stage
Add persistence or the next user-visible behavior.
```

Keep stages small enough to finish in the learner’s available session. A stage that spans unrelated architecture should be split into vertical slices.

## Skill calibration

Build a vector rather than a single level:

```json
{
  "TypeScript": "reliable",
  "React": "emerging",
  "API design": "emerging",
  "SQL": "new",
  "testing": "emerging",
  "debugging": "emerging",
  "Git": "reliable"
}
```

Combine self-report with lightweight evidence: a code prediction, a trace, and a change proposal. Do not treat the diagnostic as a gate or permanent label. Select the next stage using concept novelty, number of integration boundaries, operational risk, testability, and demonstrated evidence.

## Adaptive scaffolding

Use a fading ladder:

1. Ask a question that exposes the learner’s current model.
2. Point to a relevant source anchor or public interface.
3. Give the next decision, not the implementation.
4. Provide partial pseudocode or a smaller analogue.
5. Show a comparable worked example.
6. Review a solution only after an attempt or explicit request.

When the learner succeeds, remove one layer of scaffolding in the next stage. When the learner is stuck, split the stage or add a focused scaffold rather than generating a giant tutorial.

## Reverse-engineering trace

For a selected feature, record:

```text
user request or event
→ entrypoint or route
→ validation/authentication
→ service or state transition
→ persistence or external boundary
→ response/rendering
→ tests and failure cases
```

At each hop, cite the path, symbol, heading, or test. Mark claims as `observed`, `inferred`, or `unknown`. Ask the learner to predict the next hop before revealing it. End with a small modification, test, or explanation so the learner demonstrates transfer.

## Verification and proof

Separate evidence dimensions:

| Evidence | What it proves |
| --- | --- |
| Test output | The tested condition passed in that environment. |
| Code inspection | The implementation has a stated shape or seam. |
| Learner explanation | The learner can articulate the flow and decisions. |
| Boundary analysis | The learner considered failure, empty, malformed, unauthorized, or resource limits. |
| Transfer task | The learner can adapt the concept to a changed requirement. |
| Portfolio artifact | The learner can communicate observed work and trade-offs. |

A green test does not prove overall mastery. A correct but long implementation is still correct; give modernity or maintainability guidance separately.

## Portfolio honesty

Portfolio output may include only evidence that Upstack or Overflow observed: implemented paths, commits, tests, screenshots supplied by the learner, architecture notes, performance measurements, security checks, limitations, and actual deployment links. Label inherited, adapted, generated, or copied portions clearly. Never fabricate metrics, authorship, user counts, employment outcomes, or project impact.
