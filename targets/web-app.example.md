# Web application profile — synthetic example

```yaml
target: example-web-app
profileVersion: 1
status: example-not-validated
```

This is a fictional profile template, not a record of a deployed application.
Replace capabilities with facts verified in the consuming project. Keep real
business identities, remote IDs and credentials outside this public repository.

## Stack and ownership

Record the actual framework, runtime, language, package manager and versions.
For a component-based web project, a possible layout is a thin route layer,
domain-owned components and a shared UI package. Use the project's existing
layout; these are not required directories.

Describe which layer owns data access, business state, rendering and integration
adapters. Mark price/inventory/cart freshness requirements explicitly rather
than copying another project's caching decisions.

## Commands and previews

Populate commands only after reading project configuration and verifying the
available targets. List build, type/lint checks, scoped tests, preview and
candidate verification where supported. No command or port in this example
has been verified against a real target.

Preview should consume production components with explicit fixtures. Separate
server-only behavior and platform objects from local simulation. Select the
states and viewport/container cases relevant to the contract; do not presume
a hosted visual-regression service exists.

## Delivery and unknowns

Distinguish source changes, local preview, final build, remote deployment,
platform integration, business acceptance and release. Record missing
capabilities and evidence needed. This profile grants no external permissions.
