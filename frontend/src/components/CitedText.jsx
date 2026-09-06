import { Fragment } from "react";

const CITATION_PATTERN = /\[(\d+)\]/g;

/**
 * Splits `text` on [n] markers and renders each as a clickable chip.
 * Clicking a chip expands (and scrolls to) the matching entry in the
 * sources list below, via `onCiteClick`.
 */
export default function CitedText({ text, onCiteClick, activeIndex }) {
  const parts = [];
  let lastIndex = 0;
  let match;
  let key = 0;

  CITATION_PATTERN.lastIndex = 0;
  while ((match = CITATION_PATTERN.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(
        <Fragment key={key++}>{text.slice(lastIndex, match.index)}</Fragment>
      );
    }
    const n = Number(match[1]);
    parts.push(
      <button
        key={key++}
        type="button"
        className={`cite-chip${activeIndex === n ? " cite-chip--active" : ""}`}
        onClick={() => onCiteClick(n)}
        aria-label={`Jump to source ${n}`}
        style={{ animationDelay: `${(n - 1) * 60}ms` }}
      >
        {n}
      </button>
    );
    lastIndex = CITATION_PATTERN.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(<Fragment key={key++}>{text.slice(lastIndex)}</Fragment>);
  }

  return <p className="answer-text">{parts}</p>;
}
