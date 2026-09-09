import { useCallback, useEffect, useState } from "react";
import { fetchInvoices, createInvoice, decideInvoice, uploadInvoicePdf } from "../api.js";
import SummaryBar from "../components/SummaryBar.jsx";
import InvoiceForm from "../components/InvoiceForm.jsx";
import PdfUploadForm from "../components/PdfUploadForm.jsx";
import InvoiceTable from "../components/InvoiceTable.jsx";

export default function Dashboard({ token, userEmail, onLogout }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadInvoices = useCallback(async () => {
    setError("");
    try {
      const data = await fetchInvoices(token);
      setInvoices(data);
    } catch (err) {
      setError(err.message || "Could not load invoices");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

  async function handleCreateInvoice(invoice) {
    await createInvoice(token, invoice);
    await loadInvoices();
  }

  async function handleUploadPdf(file) {
    await uploadInvoicePdf(token, file);
    await loadInvoices();
  }

  async function handleDecision(invoiceId, decision, reason) {
    await decideInvoice(token, invoiceId, decision, reason);
    await loadInvoices();
  }

  return (
    <div className="dashboard">
      <header className="topbar">
        <span className="topbar-title">FinanceOS ‚Äî Invoice Exceptions</span>
        <div className="topbar-user">
          <span>{userEmail}</span>
          <button className="btn btn-ghost btn-small" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>

      <main className="dashboard-body">
        <SummaryBar invoices={invoices} />
        <InvoiceForm onSubmit={handleCreateInvoice} />
        <PdfUploadForm onUpload={handleUploadPdf} />

        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}

        {loading ? (
          <p className="loading-text">Loading invoices‚Ä¶</p>
        ) : (
          <InvoiceTable invoices={invoices} onDecision={handleDecision} />
        )}
      </main>
    </div>
  );
}

