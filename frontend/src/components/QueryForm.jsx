import { useState } from "react";

const EXAMPLES = [
  "What does Phase-2 add to the pipeline?",
  "How is faithfulness measured?",
  "What chunk size does ingestion use?",
];

export default function QueryForm({ onSubmit, disabled, showExamples }) {
  const [value, setValue] = useState("");

  function submit(question) {
    const q = question.trim();
    if (!q || disabled) return;
    onSubmit(q);
    setValue("");
  }

  return (
    <div className="query-form">
      {showExamples && (
        <div className="query-form__examples">
          {EXAMPLES.map((q) => (
            <button
              key={q}
              type="button"
              className="example-chip"
              onClick={() => submit(q)}
              disabled={disabled}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <form
        className="query-form__row"
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
      >
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask a question about the ingested documents…"
          disabled={disabled}
          aria-label="Ask a question"
        />
        <button type="submit" disabled={disabled || !value.trim()}>
          Ask
        </button>
      </form>
    </div>
  );
}
