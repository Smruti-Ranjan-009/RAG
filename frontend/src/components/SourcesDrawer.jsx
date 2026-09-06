import { useState } from "react";

export default function SourcesDrawer({ sources, activeIndex, onToggleActive }) {
  const [open, setOpen] = useState(false);

  if (!sources.length) return null;

  return (
    <div className="sources-drawer">
      <button
        type="button"
        className="sources-drawer__toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="sources-drawer__caret">{open ? "▾" : "▸"}</span>
        Sources ({sources.length})
      </button>

      {open && (
        <ol className="sources-drawer__list">
          {sources.map((s, i) => {
            const n = i + 1;
            return (
              <li
                key={n}
                id={`source-${n}`}
                className={`source-card${activeIndex === n ? " source-card--active" : ""}`}
              >
                <button
                  type="button"
                  className="source-card__header"
                  onClick={() => onToggleActive(n)}
                >
                  <span className="source-card__index">{n}</span>
                  <span className="source-card__name">{s.source}</span>
                  {s.rerank_score != null && (
                    <span className="source-card__score">
                      {s.rerank_score.toFixed(2)}
                    </span>
                  )}
                </button>
                <p className="source-card__snippet">{s.snippet}</p>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
