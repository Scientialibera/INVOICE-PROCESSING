import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useToken } from "../auth/useToken";
import { fetchInvoice, deleteInvoice } from "../api/client";

export default function InvoiceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { getToken } = useToken();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const token = await getToken();
        const data = await fetchInvoice(token, id);
        setInvoice(data);
      } catch (err) {
        console.error("Failed to load invoice:", err);
      } finally {
        setLoading(false);
      }
    })();
  }, [getToken, id]);

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this invoice?")) return;
    try {
      const token = await getToken();
      await deleteInvoice(token, id);
      navigate("/invoices");
    } catch (err) {
      alert("Delete failed: " + err.message);
    }
  };

  const formatCurrency = (val) =>
    val != null ? `$${Number(val).toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "--";

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="card text-center py-16">
        <p className="text-gray-400 text-lg">Invoice not found</p>
        <Link to="/invoices" className="text-primary-600 hover:underline mt-2 block">Back to Invoices</Link>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <Link to="/invoices" className="text-gray-400 hover:text-gray-600">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <h2 className="text-2xl font-bold text-gray-900 flex-1">
          {invoice.vendor_name || "Invoice"} — {invoice.invoice_number || id.slice(0, 8)}
        </h2>
        <button onClick={handleDelete} className="px-4 py-2 text-red-600 border border-red-300 rounded-lg hover:bg-red-50 text-sm">
          Delete
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="font-semibold text-lg mb-4">Invoice Details</h3>
          <dl className="space-y-3">
            {[
              ["Vendor", invoice.vendor_name],
              ["Vendor Address", invoice.vendor_address],
              ["Customer", invoice.customer_name],
              ["Invoice #", invoice.invoice_number],
              ["Date", invoice.invoice_date],
              ["Due Date", invoice.due_date],
              ["PO", invoice.purchase_order],
              ["Currency", invoice.currency],
              ["Subtotal", formatCurrency(invoice.subtotal)],
              ["Tax", formatCurrency(invoice.total_tax)],
              ["Total", formatCurrency(invoice.total_amount)],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between text-sm">
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium text-right">{value || "--"}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h3 className="font-semibold text-lg mb-4">Classification</h3>
            <dl className="space-y-3">
              <div className="flex justify-between text-sm">
                <dt className="text-gray-500">Category</dt>
                <dd>
                  <span className="px-2 py-1 bg-primary-100 text-primary-700 rounded-full text-xs">
                    {invoice.spend_category || "N/A"} / {invoice.subcategory || "N/A"}
                  </span>
                </dd>
              </div>
              <div className="flex justify-between text-sm">
                <dt className="text-gray-500">Confidence</dt>
                <dd className="font-medium">{((invoice.classification_confidence || 0) * 100).toFixed(0)}%</dd>
              </div>
              <div className="flex justify-between text-sm">
                <dt className="text-gray-500">Duplicate</dt>
                <dd>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    invoice.is_likely_duplicate ? "bg-orange-100 text-orange-700" : "bg-green-100 text-green-700"
                  }`}>
                    {invoice.is_likely_duplicate ? "Likely Duplicate" : "No"}
                  </span>
                </dd>
              </div>
              {invoice.anomaly_flags?.length > 0 && (
                <div className="text-sm">
                  <dt className="text-gray-500 mb-1">Anomaly Flags</dt>
                  <dd className="flex flex-wrap gap-1">
                    {invoice.anomaly_flags.map((flag) => (
                      <span key={flag} className="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs">
                        {flag}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
              {invoice.classification_reasoning && (
                <div className="text-sm">
                  <dt className="text-gray-500 mb-1">Reasoning</dt>
                  <dd className="text-gray-700">{invoice.classification_reasoning}</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="card">
            <h3 className="font-semibold text-lg mb-4">Metadata</h3>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between"><dt className="text-gray-500">Source</dt><dd>{invoice.source}</dd></div>
              <div className="flex justify-between"><dt className="text-gray-500">Status</dt><dd>{invoice.status}</dd></div>
              <div className="flex justify-between"><dt className="text-gray-500">Pages</dt><dd>{invoice.page_count}</dd></div>
              <div className="flex justify-between"><dt className="text-gray-500">Processed</dt><dd className="text-gray-500">{invoice.processed_at || "--"}</dd></div>
            </dl>
          </div>
        </div>
      </div>

      {invoice.line_items?.length > 0 && (
        <div className="card mt-6">
          <h3 className="font-semibold text-lg mb-4">Line Items</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 font-medium text-gray-500">#</th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500">Description</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Qty</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Unit Price</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Amount</th>
                </tr>
              </thead>
              <tbody>
                {invoice.line_items.map((li, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="py-2 px-3 text-gray-400">{i + 1}</td>
                    <td className="py-2 px-3">{li.description || "--"}</td>
                    <td className="py-2 px-3 text-right">{li.quantity ?? "--"}</td>
                    <td className="py-2 px-3 text-right">{formatCurrency(li.unit_price)}</td>
                    <td className="py-2 px-3 text-right font-medium">{formatCurrency(li.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
