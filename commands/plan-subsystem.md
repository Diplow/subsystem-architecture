---
description: Analyze a subsystem against the current feature plan to surface boundary issues, dependency concerns, and design questions
allowed-tools: ["Read", "Glob", "Grep", "Bash"]
model: opus
context: fork
---

Analyze a subsystem in the context of the current feature plan.

## Subsystem: $ARGUMENTS

Read the subsystem's context files:

1. `$ARGUMENTS/README.md` — mental model and responsibilities
2. `$ARGUMENTS/dependencies.json` — declared dependencies and type
3. `$ARGUMENTS/index.ts` — current public API

Then read parent subsystem context (child subsystems can use parent code):

4. The parent directory's `README.md` — parent's mental model and context
5. The parent directory's `dependencies.json` — sibling relationships
6. The parent directory's `index.ts` — available parent API

Then evaluate the current plan against this subsystem:

- **Boundary fit**: Does the planned change belong in this subsystem's responsibilities? Or does it bleed into a sibling's territory?
- **Dependency impact**: Will new imports be needed? Are they already declared in `dependencies.json`? If not, is this dependency justified — does it genuinely earn its place in the mental model, or does it signal a boundary problem?
- **API surface**: Will `index.ts` need new exports? Does this change the subsystem's contract with its consumers?
- **Complexity**: Will this push the subsystem past 1000 LoC or >6 files? Should a new child subsystem be introduced?
- **Design questions**: Surface anything that feels wrong — unexpected coupling, responsibilities that don't fit, or abstractions that seem forced.

## Output

Produce a **dedicated plan step** for this subsystem, ready to be included in the main feature plan:

1. **Step title**: A clear action for this subsystem (e.g., "Add `createNote` action to notes domain")
2. **Changes required**: What specifically needs to be created, modified, or deleted
3. **New dependencies**: Any imports to declare (flag if not anticipated — this may indicate a design issue)
4. **Risks or open questions**: Design concerns to resolve before implementation

If the analysis reveals that the rough plan doesn't fit this subsystem well, explain why and suggest how the overall plan should be adjusted.
