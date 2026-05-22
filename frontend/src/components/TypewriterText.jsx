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

export default function TypewriterText({ text, speed = 16, onDone }) {
  const plain = stripMd(text);
  const [n, setN] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
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
  }, [text]);

  const skip = () => {
    setN(plain.length);
    setDone(true);
    onDone && onDone();
  };

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
