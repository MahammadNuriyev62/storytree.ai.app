# StoryTree.ai — engineering spec

An interactive story-tree app. The user types a one-line story prompt; an LLM
expands it into structured metadata (title, characters, world, initial state);
then for every choice the player makes, the LLM lazily generates the next scene
on demand. Scenes are persisted in a tree of `Scene` + `Choice` rows so the
same path always replays from cache. Visualised stories layer pre-generated
character sprites and backgrounds underneath a visual-novel style UI.

## Quick start (dev)

```bash
# Backend (FastAPI + SQLite). Reads GEMINI_API_KEY from .env if present.
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# SPA build (output → static/app/, served at /app)
npm --prefix frontend install
npm --prefix frontend run build

# Open the React SPA
open http://localhost:8000/app

# Tests (mocks the LLM via tests/fakes.py — no API key needed)
pytest -q
```

DB schema lives in [db_models.py](db_models.py). New columns added during dev:
run `python -m scripts.dev_migrate` to ALTER the local SQLite (we don't use
Alembic for this project — `SQLModel.metadata.create_all` only creates new
tables, not new columns on existing ones).

## Architecture

```
                      ┌────────────────┐
        browser ────▶ │  Vite SPA      │  (/app)         frontend/
                      │  React + RR    │
                      └───────┬────────┘
                              │ fetch
                              ▼
        ┌──────────────────────────────────────────┐
        │  FastAPI (main.py)                        │
        │   /api/stories/{id}/scene  ← lazy gen    │  api.py
        │   /api/stories/{id}        ← manifest    │
        │   /static/...              ← sprites/bg  │
        └─────────────┬────────────────────────────┘
                      │
        ┌─────────────┼───────────────┐
        │             │               │
        ▼             ▼               ▼
   ChatBot         SQLite          Image cache
   (Claude CLI)    (SQLModel)      (.image_cache/)
                                   for Gemini Nano-Banana
```

- **`main.py`** — FastAPI app, mounts `/static`, mounts the SPA at `/app`.
- **`api.py`** — REST endpoints. The hot path is `GET /api/stories/{id}/scene`
  which lazily generates an empty scene's text by calling the LLM via
  `chatbot.prompt(...)`.
- **`generate.py`** — `continue_story_branch(...)` builds the system prompt
  (story metadata + world state + difficulty + stage manifest) and replays the
  branch as a conversation so the LLM sees evolution.
- **`db_models.py`** — `Story`, `Scene`, `Choice`. All world state + stage info
  is stored as JSON columns; see "Data model" below.
- **`chatbots/`** — pluggable `ChatBot` interface. Default for this repo is
  `ClaudeChatBot` which shells out to the local `claude` CLI (no API key
  needed for the chat side).
- **`ml/images/`** — image generation + sprite extraction.

## Data model

| Column                       | Type              | Notes                                                                                                       |
| ---------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------- |
| `Story.initial_state`        | JSON              | `{stats, inventory, relationships, flags}` at the start of the story.                                       |
| `Story.character_sprites`    | JSON              | Per-character expression sprite URLs (see "Visual stage"). `None` until art is generated.                   |
| `Story.backgrounds`          | JSON              | Per-setting background URLs. `None` until art is generated.                                                 |
| `Story.art_style`            | TEXT (nullable)   | LLM-emitted style guideline prepended to every per-asset art prompt.                                        |
| `Story.settings`             | JSON list         | LLM-emitted locations: `[{id, description, art_prompt}, ...]`. Drives both the auto-gen pipeline and the model's choice of `stage.setting`. |
| `Story.art_status`           | TEXT              | Art lifecycle: `none` / `pending` / `generating` / `ready` / `failed`.                                      |
| `Scene.text`                 | TEXT (nullable)   | `NULL` = unmaterialised placeholder; the API lazily generates on first fetch.                               |
| `Scene.state`                | JSON              | Full world-state snapshot as of this scene (not a delta).                                                   |
| `Scene.state_changes`        | JSON              | Short human-readable strings ("Health -10", "Found brass key").                                             |
| `Scene.pacing`               | TEXT              | `setup` / `rising` / `climax` / `resolution` — drives the SPA mood theme.                                   |
| `Scene.stage`                | JSON              | `{setting, characters_present}` — initial visual roster for page 1 (see "Visual stage").                    |
| `Choice.is_wrong`            | bool              | Costly choice — the next scene applies a penalty proportional to difficulty.                                |
| `Choice.is_pre_final`        | bool              | Picking this choice forces the next scene to be the resolution.                                             |
| `Choice.next_scene_id`       | int (nullable)    | `NULL` = terminal choice → SPA shows the "The End" card.                                                    |

**Scene id stability.** `Scene.id` is the auto-incremented DB row id and is
the canonical handle for any beat (it appears in the URL as `?scene=N`).
It's also story-agnostic: story 2's first scene happens to be id 18 because
story 1 used 1–17. Don't try to derive a "scene 1 of 5" sort of label.

## Story engine contract

- **Lazy tree.** `api.create_story` writes the root scene + one empty child
  scene + the root choice that links them. From then on, every choice click
  fetches `/scene?choice_id=X`; if the next scene's `text` is `NULL` the API
  calls `continue_story_branch` to generate it (and creates further empty
  children for that scene's new choices). Once `text` is set the scene is
  permanently cached — replaying the same branch never re-spends LLM tokens.

- **World state.** The LLM is told to emit the FULL new `state` on every scene
  (carrying unchanged values verbatim) plus a short `state_changes` list for
  the UI. State propagates through the conversation history so the model sees
  what it set last turn.

- **Pacing.** `Story.n_scenes` is a SOFT TARGET. The LLM decides when to end
  via `is_final: true` on a concluding choice. A HARD CAP triggers a forced
  resolution when `len(scenes) >= n_scenes`.

- **Difficulty.** `Story.difficulty` (0..1) maps to easy/medium/hard/impossible.
  An `is_wrong` choice is COSTLY but NOT fatal in itself — the prompt explicitly
  forbids single-choice deaths. Death emerges from cumulative state damage.

- **Resolution can be VICTORY / TRANSFORMATION / LOSS** — the model is told not
  to default to doom. STATE BALANCE rules require at least one recovery beat
  every 3-4 scenes.

## Visual stage system

Stories can ship with a pre-generated asset manifest so each scene renders
against a real background with character sprites instead of just a mood
gradient. *The Lighthouse in Winter* (story 2) is the reference implementation;
see `ml/images/lighthouse_assets.py`.

### Asset pipeline

Two paths produce the same end-state (a populated `Story.character_sprites`
+ `Story.backgrounds` manifest pointing at `static/images/.../{story_id}/`):

**A. Auto-gen from story metadata** (`POST /api/stories/{id}/generate_assets`):

1. `generate_story_metadata` (called on every `POST /api/stories`) now emits
   richly-detailed `art_prompt` fields per character + a top-level `settings`
   array with `art_prompt` per location + a top-level `art_style` string. See
   `story_example` in [generate.py](generate.py) for the schema shape.
   **Critical rule baked into the prompt**: `characters[].art_prompt` MUST
   describe ONLY the character (face, body, hair, clothing). Never include
   lighting, environment, or scene context — those leak as backdrops in the
   sprite sheet and break extraction (see "Known limitations").
2. `Story.art_status` starts as `pending` whenever the metadata generator
   produced art prompts. The SPA / a script can `POST /generate_assets` to
   trigger generation; the endpoint kicks off a FastAPI `BackgroundTask` and
   returns immediately. Status transitions: `pending → generating → ready`
   (or `failed`).
3. The background task ([ml/images/auto_gen.py](ml/images/auto_gen.py))
   composes the full prompt per asset (`art_style + art_prompt + fixed
   pose-grid scaffolding` for sprites — the scaffolding ends with a
   defensive "IGNORE any lighting/background context above"; `art_style + bg
   suffix + art_prompt` for backgrounds), calls `generate_image()`, runs
   `rembg/U²-Net` on each sprite sheet, writes to
   `static/images/.../{story_id}/`, writes the manifest onto the Story row.
4. **Tolerance for N<5 extracted sprites**: if the extractor returns fewer
   than 5 (a common failure when adjacent figures merge), the first N are
   mapped to the first N expressions and any missing slot is filled from
   `neutral`, with a warning logged. Never aborts the whole pipeline.
5. Mock-mode (`IMAGE_MOCK=1`) skips sprite extraction — placeholder PNGs are
   written directly to each expression slot so wiring can be smoke-tested
   without spending budget.
6. Cost per story at current Nano-Banana Pro pricing (~$0.15/image): 3-4
   character sheets + 4-6 backgrounds ≈ **$1.05-1.50**. The global
   `IMAGE_BUDGET_USD` cap (default $5) gates this — generation fails with
   `BudgetExceeded` if the next call would cross it.

**B. Hand-curated** (legacy, used by *The Lighthouse in Winter*):

1. The author generates a 5-pose sprite sheet per character + per-setting
   backgrounds via the free Gemini web UI using prompts pinned in a
   story-specific module.
2. Uploads land in `dev_fixtures/`. Running
   `python -m ml.images.lighthouse_assets <story_id>` copies each upload into
   `.image_cache/{hash}.png` (keyed by the SAME hash `generate_image()` would
   compute) and runs the same `rembg/U²-Net` extractor.
3. `scripts/seed_lighthouse_story.py` writes the manifest onto the Story row.

Path B is useful when you want to hand-curate every image with the free web
UI (zero $ spend), or when the auto-gen produced something you want to
override. Path A is the new default for any new story.

### Per-scene tokens (the dialect the model speaks)

The model emits `text` as markdown with these inline directives:

| Token                              | Effect                                                               |
| ---------------------------------- | -------------------------------------------------------------------- |
| `{{break}}`                        | Splits the scene into reader-controlled pages.                       |
| `{{enter:Name}}` / `{{enter:Name/expr}}` | A character walks on stage with the given expression (default neutral). |
| `{{exit:Name}}`                    | A character leaves the stage.                                        |
| `{{expression:Name/expr}}`         | A character already on stage changes mood.                           |
| `{{setting:setting_id}}`           | Swap the background to a different setting from the manifest.        |

Valid expressions: `angry`, `sad`, `smiling`, `neutral`, `scared`.

`stage.setting` and `stage.characters_present` in the JSON are the PAGE-1
state only — subsequent pages are walked forward by the tokens above. Critical
prompt rule: **if a character has an `{{enter:X}}` anywhere in the text, X
MUST NOT be in `characters_present`** (the enter token means they walk on,
they can't also be there from the start). The frontend defensively reconciles
this contradiction in `parseScene` anyway.

### Frontend rendering

- [`frontend/src/pagination.js`](frontend/src/pagination.js) — `parseScene(text,
  initialPresent, initialSetting)` walks the tokens and returns `{pages,
  rosters, settings}`, where the i-th entry is the state at the END of page i.
- [`frontend/src/components/Stage.jsx`](frontend/src/components/Stage.jsx) —
  full-cover background image + bottom-anchored sprites. Sprite positions are
  hint-based (`left` / `center` / `right` in the manifest) and land at 35% /
  50% / 62% horizontal anchor.
- [`frontend/src/pages/Play.jsx`](frontend/src/pages/Play.jsx) — VN layout
  (top-right HUD, bottom text ribbon, sprites in the middle). Page state is
  driven by `pageIndex` and `visitedPages`; revisiting a page skips the
  typewriter. URL is synced to `?scene=N&page=M` via `useSearchParams` for
  shareable deep links.

## LLM backend

The chatbot interface is the indirection point:
[`chatbots/chatbot.py`](chatbots/chatbot.py) defines `ChatBot.prompt(messages)
→ str`. Two implementations:

- **`ClaudeChatBot`** (`chatbots/claude_chatbot.py`) shells out to the local
  `claude` CLI via `--output-format json`. This is the default — works without
  an Anthropic API key because the CLI handles auth. Model names from the OpenAI
  world (`gpt-4.1-mini`, `o4-mini`) are mapped to Claude equivalents internally.
- **`OpenAIChatBot`** — only used if `OPENAI_API_KEY` is set; safe fallback.

**Image generation** uses Google Gemini via
[`ml/images/image_gen.py`](ml/images/image_gen.py) with three guardrails:

1. **Content-addressed cache** — same prompt + model + ref-images returns the
   cached PNG instantly, no API call.
2. **$5 budget cap** (`IMAGE_BUDGET_USD`) — every call appends to
   `.image_costs.jsonl`; if the next call would cross the cap, it raises
   `BudgetExceeded` instead of spending.
3. **Mock mode** — `IMAGE_MOCK=1` returns a labelled placeholder PNG for
   plumbing/dev work without spending.

`python -m ml.images.image_gen` prints a spend summary.

## Tests

[`tests/`](tests/) is a pytest safety net for the recursion engine. The LLM is
mocked at the `chatbot.prompt(...)` boundary via `tests/fakes.py::FakeChatBot`
— no network, no API key. `conftest.py` rewires `DB_NAME` to a tempdir BEFORE
importing the app so each test session gets a fresh SQLite.

What's covered (33 tests):
- `test_create_story` — root scene + root choice wiring.
- `test_cache` — re-fetching a materialised scene triggers 0 LLM calls.
- `test_recursion` — branch generation creates child scenes + choices.
- `test_pacing` / `test_termination` — `is_pre_final`, `n_scenes` hard cap.
- `test_world_state` — state carries forward through history; `is_wrong`
  applies a costlier delta than a normal choice.
- `test_tree_invariants` — exactly one root scene per story, no orphan choices.
- `test_api_contract` — DTO shape for the SPA.

CI: `pytest -m "not llm" -q` (the `llm` marker is reserved for real-API smoke
tests we never run in CI).

## Conventions / gotchas

- **Don't lose `database.db`.** Local SQLite at the repo root — gitignored.
  Use `scripts/dev_migrate.py` when adding columns, not `alembic`.
- **`dev_fixtures/`** holds source PNGs the author uploaded; `static/images/`
  holds derived sprites/backgrounds served by FastAPI. Both are committed
  for stories 2 (hand-curated), 3, and 4 (both auto-gen) so contributors
  can boot the app without regenerating.
- **Re-generating one character's sprite** (the workflow we ran for Hannah
  in story 4 after a bad extraction): edit that character's `art_prompt`
  in the Story row's `characters` JSON column, call
  `build_sprite_prompt(char, art_style)` from `auto_gen.py`, then
  `generate_image()` → `extract_sprites_from_sheet()` → write the 5
  output PNGs to the same `static/images/sprites/{story_id}/{slug}-{expr}.png`
  paths. The manifest URLs don't change, no Story row rewrite needed beyond
  the characters JSON. Costs $0.15 (one image). See `/tmp/regen_hannah.py`
  pattern.
- **Scene tree invariants** — `Story` has exactly ONE scene with no incoming
  `Choice.next_scene_id` (the root). Wiping scenes mid-tree leaves orphans
  that break the root-finder query. When mass-deleting, also clear unreachable
  scenes (the dev_migrate script doesn't do this; see ad-hoc cleanup in
  recent debugging sessions).
- **Page-1 stage rule** — `stage.characters_present` and `stage.setting` are
  the page-1 snapshot. Anything later is driven by `{{enter:}}` / `{{setting:}}`
  tokens. The frontend reconciles contradictions; the prompt forbids them.
- **No carry-over across scenes** — each generated scene starts with its own
  `stage.characters_present` (the model decides afresh). If a character was
  on stage at the end of scene N but the model omits them from N+1's roster,
  they vanish — see "Known limitations".
- **No mocks in image-gen tests** — image work is excluded from the pytest
  net because it requires the Gemini SDK + a real-or-mock API key. Manual
  validation via `python -m ml.images.lighthouse_assets <story_id>`.

## Known limitations

- **Cross-scene character continuity.** When scene N ends with Iwan on stage
  and scene N+1's prose continues that conversation, the model sometimes
  leaves N+1's `characters_present` empty — so the sprite vanishes
  mid-conversation. Possible fix: feed the prior scene's end-of-text roster
  to the prompt as "characters likely still on stage."
- **Model under-uses `{{setting:X}}`.** When prose crosses locations
  (cottage → cliff path → lighthouse door), the model often picks one
  dominant setting rather than transitioning page-by-page. The token works
  end-to-end (frontend swaps the background mid-scene) but needs prompt
  iteration to be reliably exercised.
- **Sprite extractor merges adjacent figures.** `sprite_extractor.py`
  uses connected components on a colour-distance mask. Two recurring
  failure modes: (a) lighting/scene language slips into the character
  `art_prompt` and the model paints a backdrop into the sheet that
  bridges two figures into one bbox; (b) photorealistic prompts or
  props that touch the floor (a bar, a table, dragging shadows) do the
  same. Current code: prompt rule + defensive template suffix + N<5
  tolerance with `neutral` fallback. Next-level escalations not yet
  implemented: switch extractor to fixed vertical-band slicing
  (deterministic, free), or per-pose generation (5× cost per character,
  zero merge risk).
- **Sprite layout is fixed.** Three slots (left/center/right) hard-coded in
  `Stage.jsx`. Two characters in the same slot would stack. Workable for the
  current "≤2 NPCs at a time" prompt rule; would need rethinking for crowd
  scenes.
- **No alembic.** SQLite + `dev_migrate.py` works for solo dev but ships zero
  rollback story. Production deploy would need a proper migration tool.
- **Tailwind via CDN** in the SPA — fine for dev, the build warns about it.
  Switch to PostCSS plugin before any production deploy.

## Where to look first

| If you want to...                                 | Read                                                    |
| ------------------------------------------------- | ------------------------------------------------------- |
| Understand the lazy-tree contract                 | [api.py](api.py) `get_story` + [generate.py](generate.py) `continue_story_branch` |
| Add a new visualised story (auto)                 | Create via `POST /api/stories`, then `POST /stories/{id}/generate_assets`. Logic lives in [ml/images/auto_gen.py](ml/images/auto_gen.py). |
| Add a new visualised story (hand-curated)         | [ml/images/lighthouse_assets.py](ml/images/lighthouse_assets.py) + [scripts/seed_lighthouse_story.py](scripts/seed_lighthouse_story.py) |
| Re-extract / re-generate one character's sheet    | Edit `characters[].art_prompt` in the Story row; reuse `build_sprite_prompt` + `generate_image` + `extract_sprites_from_sheet`; write to the same `static/images/sprites/{story_id}/{slug}-{expr}.png`. See "Re-generating one character's sprite" in Conventions. |
| Change what the metadata generator emits          | [generate.py](generate.py) `story_example` + `generate_story_metadata` prompt |
| Change what the model emits per scene             | [generate.py](generate.py) `OUTPUT_SCHEMA` + `_stage_block` |
| Change how a scene renders                        | [frontend/src/pages/Play.jsx](frontend/src/pages/Play.jsx) + [frontend/src/components/Stage.jsx](frontend/src/components/Stage.jsx) |
| Parse / render the inline tokens                  | [frontend/src/pagination.js](frontend/src/pagination.js) |
| Verify the recursion engine still works           | `pytest -q`                                              |
| Smoke-test the asset pipeline without spending    | `IMAGE_MOCK=1 python -m uvicorn main:app` + `POST /generate_assets` |
