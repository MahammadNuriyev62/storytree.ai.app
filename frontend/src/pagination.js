// Break a scene's prose into "pages" for a click-through reading flow.
//
// Preferred: the model emits explicit page breaks as the literal token `{{break}}`
// in the scene text — those are the model's chosen dramatic beats.
//
// Fallback: for scenes generated before the {{break}} convention (or if the model
// forgets), a greedy sentence-grouping heuristic. Each fallback page accumulates
// sentences until it reaches ~targetChars, then a new page begins. Paragraph
// breaks (\n\n) also force a page boundary.
//
// In addition, scene text can contain inline staging directions that walk a
// per-page character roster forward without being shown to the reader:
//
//   {{enter:Name}}             Name walks on with the neutral expression
//   {{enter:Name/scared}}      Name walks on with the named expression
//   {{exit:Name}}              Name leaves the stage
//   {{expression:Name/sad}}    Name (already on stage) changes expression
//
// `parseScene` returns both the cleaned page strings AND the cumulative roster
// snapshot at the END of each page, so the Stage component can render the right
// sprites without rescanning the prose.

const BREAK_TOKEN = "{{break}}";
const SENTENCE_RE = /[^.!?]+[.!?]+["')\]]*\s*|[^.!?]+$/g;
const STAGE_TOKEN_RE = /\{\{(enter|exit|expression):([^}]+)\}\}/g;
const SETTING_TOKEN_RE = /\{\{setting:([^}]+)\}\}/g;
const ANY_DIRECTIVE_RE = /\{\{(?:enter|exit|expression|setting):[^}]+\}\}/g;

export function paginate(text, targetChars = 220) {
  if (!text || !text.trim()) return [""];

  if (text.includes(BREAK_TOKEN)) {
    const pages = text.split(BREAK_TOKEN).map((p) => p.trim()).filter(Boolean);
    if (pages.length) return pages;
  }

  // --- heuristic fallback ---
  const paragraphs = text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
  const pages = [];
  for (const para of paragraphs) {
    const sentences = para.match(SENTENCE_RE) || [para];
    let buf = "";
    for (const s of sentences) {
      if (buf.length >= targetChars) {
        pages.push(buf.trim());
        buf = s;
      } else {
        buf += s;
      }
    }
    if (buf.trim()) pages.push(buf.trim());
  }
  return pages.length ? pages : [text];
}

function applyStageToken(roster, action, arg) {
  const [rawName, rawExpr] = arg.split("/").map((s) => (s || "").trim());
  if (!rawName) return;
  const expr = rawExpr || null;
  const existing = roster.find((r) => r.name === rawName);
  if (action === "enter") {
    if (existing) {
      if (expr) existing.expression = expr;
    } else {
      roster.push({ name: rawName, expression: expr || "neutral" });
    }
  } else if (action === "exit") {
    const i = roster.findIndex((r) => r.name === rawName);
    if (i >= 0) roster.splice(i, 1);
  } else if (action === "expression") {
    if (existing && expr) {
      existing.expression = expr;
    } else if (!existing && expr) {
      // Forgiving fallback: treat as enter so we still render the character.
      roster.push({ name: rawName, expression: expr });
    }
  }
}

function stripStageTokens(text) {
  return text
    .replace(ANY_DIRECTIVE_RE, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

// If a character has an explicit `{{enter:Name}}` on any non-opening page,
// they CAN'T also be in the initial roster — the model contradicted itself
// (we've observed it list the final-state cast in `stage.characters_present`
// while still emitting enter tokens at the dramatic beat). The enter token
// is more local + specific, so it wins.
function reconcileInitialRoster(initialPresent, pagesRaw) {
  const enteredLater = new Set();
  for (let i = 1; i < pagesRaw.length; i++) {
    STAGE_TOKEN_RE.lastIndex = 0;
    let m;
    while ((m = STAGE_TOKEN_RE.exec(pagesRaw[i] || "")) !== null) {
      if (m[1] !== "enter") continue;
      const [name] = m[2].split("/").map((s) => (s || "").trim());
      if (name) enteredLater.add(name);
    }
  }
  return (initialPresent || []).filter((c) => !enteredLater.has(c.name));
}

// Walk the scene text and return per-page cleaned prose + the cumulative
// character roster + active setting at the END of each page.
//   `initialPresent` seeds the roster (matches `stage.characters_present`).
//   `initialSetting` seeds the background (matches `stage.setting`).
// Inline `{{setting:X}}` tokens swap the running background going forward;
// the last token on a page wins for that page's snapshot.
export function parseScene(rawText, initialPresent = [], initialSetting = null) {
  const pagesRaw = paginate(rawText);

  const reconciled = reconcileInitialRoster(initialPresent, pagesRaw);
  const roster = reconciled.map((c) => ({
    name: c.name,
    expression: c.expression || "neutral",
  }));
  let setting = initialSetting;

  const pages = [];
  const rosters = [];
  const settings = [];

  for (const rawPage of pagesRaw) {
    STAGE_TOKEN_RE.lastIndex = 0;
    let m;
    while ((m = STAGE_TOKEN_RE.exec(rawPage)) !== null) {
      applyStageToken(roster, m[1], m[2]);
    }
    SETTING_TOKEN_RE.lastIndex = 0;
    let s;
    while ((s = SETTING_TOKEN_RE.exec(rawPage)) !== null) {
      const next = s[1].trim();
      if (next) setting = next;
    }
    pages.push(stripStageTokens(rawPage));
    rosters.push(roster.map((c) => ({ name: c.name, expression: c.expression })));
    settings.push(setting);
  }

  return { pages, rosters, settings };
}
