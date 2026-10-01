# E-pig target profile

```yaml
target: e-pig
profileVersion: 1
status: active-local
```

## Stack and commands

- One Next.js 16.2 App Router application with React 19, TypeScript 6 strict,
  Tailwind CSS 4, shadcn/ui source components, pnpm 10, and Vitest 4.
- Node 24 LTS and pnpm 10.34.5 are fixed by the project.
- Development requires an explicit market: `pnpm dev:au`, `pnpm dev:sg`, or
  `pnpm dev:us`. Do not infer a market from a Figma file or a fixture.
- Relevant verified gates are `pnpm typecheck`, `pnpm lint`,
  `pnpm test <path>`, `pnpm quality:companions`,
  `pnpm build-storybook:modules`, and `pnpm agent-doctor`.

## Source and component boundaries

- `src/app/**` owns routes, async request handling, data orchestration and
  composition. It does not own long business component implementations.
- Business UI belongs under
  `src/modules/<owning-domain>/components/<component-name>/`.
- A new or changed public business component uses the folder contract:
  `<name>.md`, `<name>.tsx`, `<name>.spec.tsx`, and
  `<name>.stories.tsx` when the component is in the Storybook/companions
  scope. Private leaf parts can remain inside `parts/`.
- Base UI without business meaning belongs in
  `packages/happy-dog/src/components`; it follows the same Storybook and test
  expectations.
- The owning domain is chosen from the business result: `catalog`, `cart`,
  `checkout`, `order`, `account`, or `content`. A page can compose several
  domains, but the route stays a thin orchestrator.

## Runtime and architecture rules

- Request APIs are async and are resolved outside `'use cache'` functions.
- Prices, inventory, cart, checkout, and payment stay request-time and are not
  placed in shared Cache Components.
- Modules consume `core/contracts` and do not import adapters, integrations,
  or vendor SDKs directly.
- Anonymous cart ids are issued by the first mutation, never by `proxy.ts`.
- Market configuration comes from the typed registry in
  `src/platform/config/markets.ts`; do not add market-specific constants to a
  component just because the design uses one market's copy.

## Preview and validation

- Business stories are aggregated by `packages/storybook-host` and run with
  `pnpm storybook:modules` on port 6007. The host uses React Vite and mocks
  `next/image` and `next/link`; it is not a full Next server runtime.
- Stories must expose the states that matter to the contract: default,
  responsive widths, empty or long content, loading/error/recovery where
  applicable, configurable or hidden media, and multiple-instance isolation.
- Cart-dependent stories use their own `CartMarketProvider` decorator and a
  dedicated market fixture. Server-only APIs, Server Actions, adapters, and
  real network calls need a boundary fixture or an integration-level test.
- Visual comparison keeps the Figma source, viewport, font, asset, content,
  state, and renderer version fixed. A successful Storybook build or a matching
  computed value is not visual acceptance.
- Current E-pig does not provide a Chromatic-style blocking visual gate. Record
  browser/manual comparison evidence and the unverified scope explicitly.

## Delivery boundary

The normal DTC delivery for E-pig is source code, component companions,
Storybook preview, and recorded checks. A route integration, live market
preview, deployment, or business acceptance is an additional layer and must be
reported separately. The profile does not grant permission to publish, send
messages, modify merchant systems, or claim production readiness.

## Precedence and unknowns

E-pig precedence is `AGENTS.md Hard Rules > e-pig rules > e-pig-dev-loop >
community skills > DTC target profile`. When a rule, command, component
boundary, or asset source is unknown, retain the unknown and ask for the
smallest decision that unblocks the affected work.
