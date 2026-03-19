import { useState, useCallback } from "react";
import { useToken } from "../auth/useToken";
import { uploadInvoice } from "../api/client";

export default function UploadPage() {
  const { getToken } = useToken();
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState([]);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback((newFiles) => {
    const valid = Array.from(newFiles).filter((f) =>
      ["application/pdf", "image/png", "image/jpeg", "image/tiff"].includes(f.type)
    );
    setFiles((prev) => [...prev, ...valid]);
  }, []);

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const upload = async () => {
    if (!files.length) return;
    setUploading(true);
    const token = await getToken();
    const uploadResults = [];

    for (const file of files) {
      try {
        const result = await uploadInvoice(token, file);
        uploadResults.push({ file: file.name, status: "success", data: result });
      } catch (err) {
        uploadResults.push({ file: file.name, status: "error", error: err.message });
      }
    }

    setResults(uploadResults);
    setFiles([]);
    setUploading(false);
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Upload Invoices</h2>

      <div
        className={`card border-2 border-dashed text-center py-16 transition-colors cursor-pointer ${
          dragOver ? "border-primary-400 bg-primary-50" : "border-gray-300 hover:border-gray-400"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => document.getElementById("file-input").click()}
      >
        <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        <p className="text-lg text-gray-600 mb-1">Drop invoices here or click to browse</p>
        <p className="text-sm text-gray-400">PDF, PNG, JPG, TIFF (max 25 MB each)</p>
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <div className="card mt-4">
          <h3 className="font-semibold mb-3">Files to Upload ({files.length})</h3>
          <ul className="space-y-2">
            {files.map((file, i) => (
              <li key={i} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm">{file.name}</span>
                  <span className="text-xs text-gray-400">{formatSize(file.size)}</span>
                </div>
                <button onClick={() => removeFile(i)} className="text-red-400 hover:text-red-600 text-sm">
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <button onClick={upload} disabled={uploading} className="btn-primary mt-4">
            {uploading ? "Uploading..." : `Upload ${files.length} file${files.length > 1 ? "s" : ""}`}
          </button>
        </div>
      )}

      {results.length > 0 && (
        <div className="card mt-4">
          <h3 className="font-semibold mb-3">Upload Results</h3>
          <ul className="space-y-2">
            {results.map((r, i) => (
              <li key={i} className={`flex items-center gap-3 py-2 px-3 rounded-lg ${
                r.status === "success" ? "bg-green-50" : "bg-red-50"
              }`}>
                <span className={`w-2 h-2 rounded-full ${r.status === "success" ? "bg-green-500" : "bg-red-500"}`} />
                <span className="text-sm flex-1">{r.file}</span>
                <span className={`text-xs ${r.status === "success" ? "text-green-600" : "text-red-600"}`}>
                  {r.status === "success" ? "Uploaded" : r.error}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
