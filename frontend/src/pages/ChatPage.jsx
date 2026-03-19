import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { useToken } from "../auth/useToken";
import { streamChat } from "../api/client";

export default function ChatPage() {
  const { getToken } = useToken();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const endRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);

    const assistantIdx = messages.length + 1;
    setMessages((prev) => [...prev, { role: "assistant", content: "", chunks: [] }]);

    try {
      const token = await getToken();
      abortRef.current = streamChat(
        token,
        text,
        (chunk) => {
          setMessages((prev) => {
            const updated = [...prev];
            const msg = { ...updated[assistantIdx] };
            msg.chunks = [...(msg.chunks || []), chunk];

            if (chunk.type === "text") {
              msg.content += chunk.content;
            } else if (chunk.type === "tool_call") {
              msg.content += `\n\n*Calling tool: ${chunk.name}...*\n`;
            } else if (chunk.type === "code") {
              msg.content += `\n\`\`\`python\n${chunk.content}\n\`\`\`\n`;
            } else if (chunk.type === "code_output") {
              msg.content += `\n**Output:**\n\`\`\`\n${chunk.content}\n\`\`\`\n`;
            }

            updated[assistantIdx] = msg;
            return updated;
          });
        },
        () => setStreaming(false),
        (err) => {
          setMessages((prev) => {
            const updated = [...prev];
            updated[assistantIdx] = {
              ...updated[assistantIdx],
              content: updated[assistantIdx].content + `\n\n*Error: ${err}*`,
            };
            return updated;
          });
          setStreaming(false);
        }
      );
    } catch (err) {
      setStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Chat with SpendAnalyzer</h2>

      <div className="flex-1 overflow-auto card mb-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-lg mb-2">Ask anything about your invoices</p>
            <div className="space-y-2 text-sm">
              <p>"What's my total spend this quarter?"</p>
              <p>"Show me all invoices from Microsoft"</p>
              <p>"Are there any duplicate invoices?"</p>
              <p>"Create a chart of spend by category"</p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-primary-600 text-white"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{msg.content || "..."}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm">{msg.content}</p>
              )}
            </div>
          </div>
        ))}
        {streaming && (
          <div className="flex justify-start">
            <div className="flex gap-1 px-4 py-3">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask about your invoices..."
          className="input-field flex-1"
          disabled={streaming}
        />
        <button onClick={send} disabled={streaming || !input.trim()} className="btn-primary">
          Send
        </button>
      </div>
    </div>
  );
}
