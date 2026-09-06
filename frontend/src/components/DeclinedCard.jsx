export default function DeclinedCard({ reason }) {
  const isInsufficientContext = reason === "model signaled insufficient context";

  const message = isInsufficientContext
    ? "No supporting evidence found in the source documents."
    : "The answer cited a source that wasn't actually retrieved, so it was withheld rather than shown unverified.";

  return (
    <div className="declined-card">
      <span className="declined-card__mark" aria-hidden="true">
        ⊘
      </span>
      <p>{message}</p>
    </div>
  );
}
