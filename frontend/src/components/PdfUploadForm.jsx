import { useRef, useState } from "react";

export default function PdfUploadForm({ onUpload }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  function handleFileChange(e) {
    setError("");
    setFile(e.target.files?.[0] || null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError("Choose a PDF file first.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onUpload(file);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      // Backend returns a specific, readable message for extraction
      // failures (missing fields, unreadable PDF, scanned image with
      // no text layer) — shown as-is rather than a generic fallback,
      // since that message is the whole point of "handle extraction
      // failures gracefully."
      setError(err.message || "Could not process this PDF");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel">
      <h2>Upload a PDF invoice</h2>
      <form className="pdf-upload-form" onSubmit={handleSubmit}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          aria-label="Choose a PDF invoice file"
        />
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Uploading…" : "Upload PDF invoice"}
        </button>
      </form>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
    </section>
  );
}
