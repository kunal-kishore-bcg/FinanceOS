import { Fragment, useState } from "react";
import RecommendationBadge from "./RecommendationBadge.jsx";

const DECISION_LABELS = { approve: "Approve", escalate: "Escalate", reject: "Reject" };

function deriveStatus(invoice) {
  if (!invoice.reviewed_by) {
    return { label: "Pending", className: "status-pending", decision: null };
  }
  if (invoice.human_override) {
    return { label: "Overridden", className: "status-overridden", decision: invoice.status };
  }
  return { label: "Confirmed", className: "status-confirmed", decision: invoice.status };
}

function formatCurrency(amount) {
  return amount.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function DecisionForm({ invoice, onSubmit, onCancel }) {
  const [decision, setDecision] = useState(invoice.ai_recommendation || "approve");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!reason.trim()) {
      setError("Enter a reason for this decision.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit(invoice.id, decision, reason.trim());
    } catch (err) {
      setError(err.message || "Could not save decision");
      setSubmitting(false);
    }
  }

  return (
    <form className="decision-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor={`decision-${invoice.id}`}>Decision</label>
        <select id={`decision-${invoice.id}`} value={decision} onChange={(e) => setDecision(e.target.value)}>
          <option value="approve">Approve</option>
          <option value="escalate">Escalate</option>
          <option value="reject">Reject</option>
        </select>
      </div>
      <div className="field field-grow">
        <label htmlFor={`reason-${invoice.id}`}>Reason</label>
        <input
          id={`reason-${invoice.id}`}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Why are you making this call?"
          autoFocus
        />
      </div>
      <div className="field field-actions">
        <button type="submit" className="btn btn-primary btn-small" disabled={submitting}>
          {submitting ? "Saving…" : "Save decision"}
        </button>
        <button type="button" className="btn btn-ghost btn-small" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
    </form>
  );
}

export default function InvoiceTable({ invoices, onDecision }) {
  const [openRowId, setOpenRowId] = useState(null);

  async function handleConfirm(invoice) {
    await onDecision(invoice.id, invoice.ai_recommendation, "Confirmed AI recommendation");
  }

  if (invoices.length === 0) {
    return <p className="empty-state">No invoices yet — submit one above to get started.</p>;
  }

  return (
    <section className="panel">
      <h2>Invoices</h2>
      <table className="invoice-table">
        <thead>
          <tr>
            <th>Invoice #</th>
            <th>Vendor</th>
            <th>Amount</th>
            <th>PO reference</th>
            <th>AI recommendation</th>
            <th>Confidence</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((invoice) => {
            const statusInfo = deriveStatus(invoice);
            const isPending = statusInfo.label === "Pending";
            const isOpen = openRowId === invoice.id;

            return (
              <Fragment key={invoice.id}>
                <tr className={isOpen ? "row-open" : ""}>
                  <td>{invoice.invoice_number}</td>
                  <td>{invoice.vendor_name}</td>
                  <td className="cell-amount">{formatCurrency(invoice.amount)}</td>
                  <td>{invoice.po_number || <span className="cell-muted">None provided</span>}</td>
                  <td>
                    <RecommendationBadge recommendation={invoice.ai_recommendation} />
                  </td>
                  {/* The API doesn't return a confidence score yet — see the
                      note where this table is introduced. Shown honestly
                      rather than invented or left blank. */}
                  <td className="cell-muted">Not provided by AI</td>
                  <td>
                    <span className={`status-pill ${statusInfo.className}`}>{statusInfo.label}</span>
                    {statusInfo.decision && (
                      <span className="status-detail">
                        {" "}
                        → {DECISION_LABELS[statusInfo.decision] || statusInfo.decision}
                      </span>
                    )}
                  </td>
                  <td className="cell-actions">
                    {isPending ? (
                      <div className="action-buttons">
                        {invoice.ai_recommendation && (
                          <button className="btn btn-confirm btn-small" onClick={() => handleConfirm(invoice)}>
                            Confirm
                          </button>
                        )}
                        <button
                          className="btn btn-override btn-small"
                          onClick={() => setOpenRowId(isOpen ? null : invoice.id)}
                        >
                          {invoice.ai_recommendation ? "Override" : "Make decision"}
                        </button>
                      </div>
                    ) : (
                      <span className="cell-muted">Reviewed</span>
                    )}
                  </td>
                </tr>
                {isOpen && (
                  <tr className="row-form">
                    <td colSpan={8}>
                      <DecisionForm
                        invoice={invoice}
                        onSubmit={async (id, decision, reason) => {
                          await onDecision(id, decision, reason);
                          setOpenRowId(null);
                        }}
                        onCancel={() => setOpenRowId(null)}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
