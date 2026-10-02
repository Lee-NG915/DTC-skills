# Target profiles

DTC skills are reusable workflow instructions. A target profile supplies the
project-specific facts that the workflow must consume before it chooses paths,
commands, component boundaries, preview tools, or delivery claims.

## Resolution

When a DTC skill is used inside a project, resolve the profile in this order:

1. Read the project root `.dtc/target-profile.md` when it exists.
2. If the project documents another profile path, use that path and record it
   in the context summary.
3. If no profile is available, use the generic cross-technology rules and mark
   project-specific commands, boundaries, and acceptance layers as unknown.

The profile is a context input, not a permission grant. Project `AGENTS.md`,
security rules, user authorization, and runtime capabilities still take
precedence. A profile must never invent credentials, remote access, business
acceptance, or production status.

## Profile contract

Each profile should record:

- target id and profile version;
- framework, language, package manager, build and test tools;
- source layout and domain ownership rules;
- component contract and preview/story requirements;
- responsive baselines, asset/font constraints, and visual evidence tools;
- commands that were verified in the target project;
- delivery layers and explicit non-goals;
- project rules that override generic DTC guidance;
- unknowns and the evidence needed to resolve them.

Skills consume this information through the context summary. They should adapt
their workflow to the profile while keeping the same evidence boundaries:
design evidence, implementation, tests, visual validation, user acceptance,
and deployment remain separate results.

The profile is intentionally a small, reviewable document. Put detailed
framework instructions in the target project's own rules or in a dedicated
skill; do not turn this directory into a second project handbook.
