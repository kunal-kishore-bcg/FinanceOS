import { useState } from "react";

const EMPTY_FORM = { invoice_number: "", vendor_name: "", po_number: "", amount: "" };

export default function InvoiceForm({ onSubmit }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!form.invoice_number.trim() || !form.vendor_name.trim() || !form.amount) {
      setError("Invoice number, vendor, and amount are required.");
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit({
        invoice_number: form.invoice_number.trim(),
        vendor_name: form.vendor_name.trim(),
        po_number: form.po_number.trim() || null,
        amount: Number(form.amount),
      });
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err.message || "Could not submit invoice");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel">
      <h2>Submit an invoice</h2>
      <form className="invoice-form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="invoice_number">Invoice #</label>
          <input
            id="invoice_number"
            value={form.invoice_number}
            onChange={(e) => update("invoice_number", e.target.value)}
            placeholder="INV-016"
          />
        </div>
        <div className="field">
          <label htmlFor="vendor_name">Vendor name</label>
          <input
            id="vendor_name"
            value={form.vendor_name}
            onChange={(e) => update("vendor_name", e.target.value)}
            placeholder="Acme Consulting Ltd"
          />
        </div>
        <div className="field">
          <label htmlFor="po_number">PO reference</label>
          <input
            id="po_number"
            value={form.po_number}
            onChange={(e) => update("po_number", e.target.value)}
            placeholder="Leave blank if none"
          />
        </div>
        <div className="field">
          <label htmlFor="amount">Amount ($)</label>
          <input
            id="amount"
            type="number"
            min="0"
            step="0.01"
            value={form.amount}
            onChange={(e) => update("amount", e.target.value)}
            placeholder="0.00"
          />
        </div>
        <div className="field field-submit">
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Submitting…" : "Submit invoice"}
          </button>
        </div>
      </form>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
    </section>
  );
}
