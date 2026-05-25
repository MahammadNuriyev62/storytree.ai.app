import { useEffect, useState } from "react";
import { marked } from "marked";

// Strip markdown emphasis for the typing phase, then render full markdown.
function stripMd(s) {
  return (s || "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    .replace(/_(.*?)_/g, "$1");
}

export default function TypewriterText({ text, speed = 16, onDone, instant = false }) {
  const plain = stripMd(text);
  const [n, setN] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (instant) {
      // Revisiting a page the reader has already seen — render fully + fire
      // onDone immediately so the Next button / choices appear without delay.
      setN(plain.length);
      setDone(true);
      onDone && onDone();
      return;
    }
    setN(0);
    setDone(false);
    let i = 0;
    const id = setInterval(() => {
      i += 2;
      if (i >= plain.length) {
        setN(plain.length);
        setDone(true);
        clearInterval(id);
        onDone && onDone();
      } else {
        setN(i);
      }
    }, speed);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, instant]);

  const skip = () => {
    setN(plain.length);
    setDone(true);
    onDone && onDone();
  };

  // Space (or Enter) while the typewriter is running reveals the rest of the
  // page instantly. Play.jsx's own keydown handler is gated on `pageDone` so
  // the two don't fight — this handles Space-while-typing; Play handles
  // Space-when-done.
  useEffect(() => {
    if (done || instant) return;
    const onKey = (e) => {
      if (e.key !== " " && e.key !== "Enter") return;
      const t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      e.preventDefault();
      skip();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done, instant]);

  if (done) {
    return (
      <div
        className="scene-prose text-lg leading-relaxed"
        dangerouslySetInnerHTML={{ __html: marked.parse(text || "") }}
      />
    );
  }
  return (
    <div
      onClick={skip}
      title="Click to reveal"
      className="scene-prose text-lg leading-relaxed whitespace-pre-wrap cursor-pointer"
    >
      {plain.slice(0, n)}
      <span className="opacity-60 animate-pulse">▌</span>
    </div>
  );
}
