import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useToken } from "../auth/useToken";
import { fetchInvoices } from "../api/client";

export default function InvoicesPage() {
  const { getToken } = useToken();
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const token = await getToken();
        const data = await fetchInvoices(token, page * PAGE_SIZE, PAGE_SIZE);
        setInvoices(data);
      } catch (err) {
        console.error("Failed to load invoices:", err);
      } finally {
        setLoading(false);
      }
    })();
  }, [getToken, page]);

  const formatCurrency = (val) =>
    val != null ? `$${Number(val).toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "--";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Invoices</h2>
        <Link to="/upload" className="btn-primary">Upload New</Link>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : invoices.length === 0 ? (
        <div className="card text-center py-16">
          <p className="text-gray-400 text-lg mb-2">No invoices found</p>
          <Link to="/upload" className="text-primary-600 hover:underline">Upload your first invoice</Link>
        </div>
      ) : (
        <>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-3 font-medium text-gray-500">Vendor</th>
                  <th className="text-left py-3 px-3 font-medium text-gray-500">Invoice #</th>
                  <th className="text-right py-3 px-3 font-medium text-gray-500">Amount</th>
                  <th className="text-left py-3 px-3 font-medium text-gray-500">Category</th>
                  <th className="text-left py-3 px-3 font-medium text-gray-500">Date</th>
                  <th className="text-left py-3 px-3 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-3 font-medium text-gray-500">Flags</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="py-3 px-3">
                      <Link to={`/invoices/${inv.id}`} className="text-primary-600 hover:underline font-medium">
                        {inv.vendor_name || "Unknown"}
                      </Link>
                    </td>
                    <td className="py-3 px-3 text-gray-500">{inv.invoice_number || "--"}</td>
                    <td className="py-3 px-3 text-right font-medium">{formatCurrency(inv.total_amount)}</td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-1 bg-gray-100 rounded-full text-xs">{inv.spend_category || "N/A"}</span>
                    </td>
                    <td className="py-3 px-3 text-gray-500">{inv.invoice_date || "N/A"}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        inv.status === "processed" ? "bg-green-100 text-green-700" :
                        inv.status === "failed" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                      }`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      {inv.anomaly_flags?.length > 0 && (
                        <span className="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs">
                          {inv.anomaly_flags.length} flag{inv.anomaly_flags.length > 1 ? "s" : ""}
                        </span>
                      )}
                      {inv.is_likely_duplicate && (
                        <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded-full text-xs ml-1">
                          Duplicate
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex justify-between mt-4">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-secondary"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500 self-center">Page {page + 1}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={invoices.length < PAGE_SIZE}
              className="btn-secondary"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
