# Project Configuration

> **This file is the install template** (in the workflow repo it lives at `dev_cycle/project.md`).
> `install.sh` copies it to **`.dev_cycle/project.md`** in your application project.
>
> **`/init-dev-cycle` rewrites `.dev_cycle/project.md`** in whatever project you have open — not
> this template path. If you are editing the workflow package and still see HTML comments here,
> that is expected; your personalized file is **`.dev_cycle/project.md`** next to your app code.
>
> Single source of truth for project-specific context. All agents read **`.dev_cycle/project.md`**.
> Edit freely after `/init-dev-cycle`.

---

## Project

**Name:** <!-- e.g. MyApp -->
**Description:** <!-- e.g. A fitness tracking app for personal trainers and their clients -->
**Stack:** <!-- e.g. Flutter + Supabase, React Native + FastAPI, Next.js + Prisma + Postgres -->
**Repo:** <!-- e.g. ~/code/myapp -->

---

## Tech Stack Details

<!-- Describe the key frameworks, libraries, and tools in use.
     Be specific enough that an agent can make correct technology choices.

     Example (Flutter):
       - Flutter 3.x with Dart
       - Riverpod for state management (AsyncNotifier pattern)
       - Freezed + json_serializable for models (run build_runner after model changes)
       - Supabase for backend (auth, database, storage)
       - Feature-first folder structure: lib/features/<name>/{data,domain,presentation}/

     Example (React Native + FastAPI):
       - React Native with Expo
       - Zustand for state management
       - FastAPI + SQLAlchemy + SQLite backend
       - Pydantic schemas for all API request/response types
       - pytest for backend tests, Jest + React Native Testing Library for frontend
-->

---

## Architecture Patterns

<!-- Rules agents must follow. Be explicit — agents will enforce these.

     Example:
       - All Supabase calls must go through repository classes (never in providers/widgets)
       - Use AsyncValue.error with a retry button for every async UI operation
       - New DB columns always added via _apply_migrations pattern (never recreate tables)
       - Providers never import from other feature's presentation layer
-->

---

## Wave Structure

<!-- How to break implementation into waves (ordered by dependency).
     Customize for your stack.

     Default (3-wave):
       Wave 1: Data layer — models, schemas, DB migrations
       Wave 2: Business logic — services, API routes, state management
       Wave 3: UI/presentation — screens, components, final wiring

     Example (Flutter):
       Wave 1: Freezed models + DB schema changes + build_runner
       Wave 2: Repository methods + Riverpod providers
       Wave 3: Screen widgets + navigation wiring

     Example (FastAPI + React):
       Wave 1: SQLAlchemy models + Pydantic schemas + migrations
       Wave 2: FastAPI routers + service layer
       Wave 3: React components + Zustand store updates
-->

---

## Gate Commands

<!-- Human-readable description of what runs at each gate.
     The actual commands live in dev_cycle/gates_config.sh.

     Example:
       Wave:   flutter analyze + flutter test
       Pre-PR: same + full codegen rebuild
       Final:  flutter clean + pub get + codegen + analyze + test
-->

- **Wave:** <!-- describe -->
- **Pre-PR:** <!-- describe -->
- **Final:** <!-- describe -->

---

## Models

<!-- Which Claude model to use for each agent type.
     Available models (as of 2025):
       claude-opus-4-6      — strongest reasoning, highest cost (~$15/MTok)
       claude-sonnet-4-6    — fast, capable, lower cost (~$6/MTok)
       claude-haiku-4-5-20251001 — fastest, cheapest (~$1/MTok), for simple tasks

     Default tiering rationale:
       Design/Build use Opus — architecture decisions and code generation benefit from
         stronger reasoning. Mistakes here are expensive to fix downstream.
       Review/Fix/Deploy use Sonnet — reading, checking, and targeted edits don't need
         full reasoning power. Saves cost without sacrificing quality.
-->

| Agent | Model | Reason |
|-------|-------|--------|
| design | <!-- e.g. claude-opus-4-6 --> | <!-- e.g. Architecture decisions need strong reasoning --> |
| build | <!-- e.g. claude-opus-4-6 --> | <!-- e.g. TDD + code generation benefits from best model --> |
| review | <!-- e.g. claude-sonnet-4-6 --> | <!-- e.g. Reading + checking, not architecture design --> |
| fix | <!-- e.g. claude-sonnet-4-6 --> | <!-- e.g. Targeted edits to existing code --> |
| deploy | <!-- e.g. claude-sonnet-4-6 --> | <!-- e.g. Mechanical startup + log monitoring --> |

---

## Branch Naming

Branch prefix: `dev-`
<!-- Full pattern: dev-<slug>-<N>  e.g. dev-model-selector-1 -->

---

## Code Style Notes

<!-- Anything agents should know about naming, formatting, or file organization.

     Example:
       - Widget files: snake_case.dart (e.g. feed_screen.dart)
       - Test files mirror lib/ structure under test/
       - No print() calls — use logger package
       - Max widget build method: ~80 lines, extract sub-widgets beyond that
-->
