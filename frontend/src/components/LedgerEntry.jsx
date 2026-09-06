import { useState } from "react";
import CitedText from "./CitedText.jsx";
import SourcesDrawer from "./SourcesDrawer.jsx";
import DeclinedCard from "./DeclinedCard.jsx";

export default function LedgerEntry({ entry }) {
  const [activeIndex, setActiveIndex] = useState(null);

  function handleCiteClick(n) {
    setActiveIndex(n);
    const el = document.getElementById(`source-${n}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  return (
    <article className="ledger-entry">
      <p className="ledger-entry__question">{entry.question}</p>

      {entry.status === "loading" && (
        <p className="ledger-entry__loading">Retrieving and reading sources…</p>
      )}

      {entry.status === "error" && (
        <p className="ledger-entry__error">{entry.error}</p>
      )}

      {entry.status === "done" && entry.accepted && (
        <>
          <CitedText
            text={entry.answer}
            onCiteClick={handleCiteClick}
            activeIndex={activeIndex}
          />
          <SourcesDrawer
            sources={entry.sources}
            activeIndex={activeIndex}
            onToggleActive={handleCiteClick}
          />
        </>
      )}

      {entry.status === "done" && !entry.accepted && (
        <DeclinedCard reason={entry.reason} />
      )}
    </article>
  );
}
