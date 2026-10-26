import { useState, useRef, useEffect } from "react";
import {
  BrainCircuit, FileUp, Send, FileText,
  LoaderCircle, Plus, MessageSquare, AlertCircle
} from "lucide-react";
import "./App.css";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileInput = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function uploadPDF(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    setError("");

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF document.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("The PDF must be smaller than 10 MB.");
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

     setDocuments((previous) => [
      ...previous.filter((doc) => doc.name !== file.name),
      {
        id: data.document_id || Date.now(),
        name: file.name,
        pages: data.total_pages,
        chunks: data.chunks_stored,
      },
    ]);

    } catch (err) {
      setError(err.message || "Unable to upload PDF.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function sendMessage(event) {
    event.preventDefault();

    const text = question.trim();
    if (!text || loading) return;

    setQuestion("");
    setError("");

    setMessages((previous) => [
      ...previous,
      { role: "user", content: text },
    ]);

    setLoading(true);

    try {
      const response = await fetch(`${API}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: text,
          top_k: 5,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "AI request failed");
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources || [],
        },
      ]);

    } catch (err) {
      setError(err.message || "Could not contact the AI backend.");

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: "Sorry, I could not process your question.",
          sources: [],
        },
      ]);

    } finally {
      setLoading(false);
    }
  }

  function newChat() {
    setMessages([]);
    setQuestion("");
    setError("");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <BrainCircuit size={24} />
          </div>
          <div>
            <h2>Enterprise AI</h2>
            <p>Knowledge Assistant</p>
          </div>
        </div>

        <button className="new-chat" onClick={newChat}>
          <Plus size={18} />
          New conversation
        </button>

        <div className="sidebar-section">
          <div className="section-heading">
            <span>DOCUMENTS</span>
            <span>{documents.length}</span>
          </div>

          {documents.length === 0 ? (
            <p className="muted">No documents uploaded this session.</p>
          ) : (
            <div className="document-list">
              {documents.map((doc) => (
                <div className="document" key={doc.id}>
                  <FileText size={18} />
                  <div>
                    <strong title={doc.name}>{doc.name}</strong>
                    <small>{doc.pages} pages · {doc.chunks} chunks</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <button
          className="upload-button"
          onClick={() => fileInput.current?.click()}
          disabled={uploading}
        >
          {uploading
            ? <LoaderCircle className="spin" size={18} />
            : <FileUp size={18} />}
          {uploading ? "Processing PDF..." : "Upload PDF"}
        </button>

        <input
          ref={fileInput}
          type="file"
          accept=".pdf,application/pdf"
          hidden
          onChange={uploadPDF}
        />

        <div className="sidebar-footer">
          <span className="status-dot" />
          FastAPI · LangChain · ChromaDB
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>Knowledge Assistant</h1>
            <p>Ask questions about your indexed documents</p>
          </div>
          <span className="model-label">RAG Powered</span>
        </header>

        <section className="chat-area">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-icon">
                <BrainCircuit size={36} />
              </div>
              <h2>What would you like to know?</h2>
              <p>
                Upload a PDF document, then ask questions.
                Answers are generated using retrieved passages.
              </p>

              <div className="suggestions">
                {[
                  "Summarise the research findings",
                  "What methodology was used?",
                  "What factors affect impulsive buying?",
                ].map((item) => (
                  <button
                    key={item}
                    onClick={() => setQuestion(item)}
                  >
                    <MessageSquare size={16} />
                    {item}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <div
                  className={`message ${message.role}`}
                  key={index}
                >
                  <div className="message-avatar">
                    {message.role === "assistant"
                      ? <BrainCircuit size={20} />
                      : "You"}
                  </div>

                  <div className="message-body">
                    <div className="message-role">
                      {message.role === "assistant"
                        ? "AI Assistant"
                        : "You"}
                    </div>

                    <div className="message-text">
                      {message.content}
                    </div>

                    {message.sources?.length > 0 && (
                      <div className="sources">
                        <h4>Retrieved sources</h4>

                        {message.sources.map((source, i) => (
                          <details key={i} className="source">
                            <summary>
                              <FileText size={15} />
                              <span>{source.filename}</span>
                              {source.similarity != null && (
                              <small>
                                {Math.round(source.similarity * 100)}%similarity
                              </small>
                              )}
                            </summary>
                            <p>{source.text}</p>
                          </details>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="thinking">
                  <LoaderCircle className="spin" size={18} />
                  AI is generating an answer...
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </section>

        <div className="composer-area">
          {error && (
            <div className="error-banner">
              <AlertCircle size={17} />
              {error}
            </div>
          )}

          <form className="composer" onSubmit={sendMessage}>
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a question about your documents..."
              disabled={loading}
              aria-label="Ask a question"
            />

            <button
              type="submit"
              disabled={!question.trim() || loading}
              aria-label="Send message"
            >
              <Send size={20} />
            </button>
          </form>

          <p className="disclaimer">
            AI-generated answers may contain mistakes. Verify important details.
          </p>
        </div>
      </main>
    </div>
  );
}