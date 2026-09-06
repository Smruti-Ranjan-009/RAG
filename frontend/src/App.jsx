import { useEffect, useRef, useState } from "react";
import StatusBar from "./components/StatusBar.jsx";
import QueryForm from "./components/QueryForm.jsx";
import LedgerEntry from "./components/LedgerEntry.jsx";
import { askQuestion, checkHealth } from "./api.js";
import "./App.css";

export default function App() {
  const [connected, setConnected] = useState(null);
  const [entries, setEntries] = useState([]);
  const feedEndRef = useRef(null);

  useEffect(() => {
    checkHealth().then(setConnected);
  }, []);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length]);

  const busy = entries.some((e) => e.status === "loading");

  async function handleSubmit(question) {
    const id = crypto.randomUUID();
    setEntries((prev) => [...prev, { id, question, status: "loading" }]);

    try {
      const result = await askQuestion(question);
      setEntries((prev) =>
        prev.map((e) =>
          e.id === id
            ? {
                ...e,
                status: "done",
                answer: result.answer,
                sources: result.sources,
                accepted: result.accepted,
                reason: result.reason,
              }
            : e
        )
      );
    } catch (err) {
      setEntries((prev) =>
        prev.map((e) =>
          e.id === id ? { ...e, status: "error", error: err.message } : e
        )
      );
    }
  }

  return (
    <div className="app">
      <StatusBar connected={connected} />

      <main className="feed">
        {entries.length === 0 && (
          <p className="feed__empty">
            Answers here trace back to an exact source chunk, or say plainly
            when the documents don't support one.
          </p>
        )}

        {entries.map((entry) => (
          <LedgerEntry key={entry.id} entry={entry} />
        ))}
        <div ref={feedEndRef} />
      </main>

      <footer className="composer">
        <QueryForm
          onSubmit={handleSubmit}
          disabled={busy || connected === false}
          showExamples={entries.length === 0}
        />
      </footer>
    </div>
  );
}
