export default function StatusBar({ connected }) {
  return (
    <header className="status-bar">
      <span className="status-bar__title">RAG Ledger</span>
      <span className={`status-bar__dot${connected ? " status-bar__dot--ok" : ""}`} />
      <span className="status-bar__label">
        {connected === null ? "connecting…" : connected ? "ready" : "unreachable"}
      </span>
    </header>
  );
}
