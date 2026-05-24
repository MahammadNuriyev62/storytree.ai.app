// Break a scene's prose into "pages" for a click-through reading flow.
//
// Preferred: the model emits explicit page breaks as the literal token `{{break}}`
// in the scene text — those are the model's chosen dramatic beats.
//
// Fallback: for scenes generated before the {{break}} convention (or if the model
// forgets), a greedy sentence-grouping heuristic. Each fallback page accumulates
// sentences until it reaches ~targetChars, then a new page begins. Paragraph
// breaks (\n\n) also force a page boundary.

const BREAK_TOKEN = "{{break}}";
const SENTENCE_RE = /[^.!?]+[.!?]+["')\]]*\s*|[^.!?]+$/g;

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
