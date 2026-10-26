import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  BrainCircuit, Plus, FileText, Send, Sparkles,
  Menu, X, Moon, Sun, Copy, Check, AlertCircle,
  LoaderCircle, MessageSquare, Database, ShieldCheck,
  ChevronDown, UploadCloud, BookOpen,
  ArrowLeft, ArrowRight, Trash2, RefreshCw
} from "lucide-react";

import "./App.css";

const API = import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const suggestions = [
  {
    title: "Research overview",
    question: "Summarise the research objective, methodology and main findings."
  },
  {
    title: "Research methodology",
    question: "What research methodology and data collection methods were used?"
  },
  {
    title: "Key variables",
    question: "What are the key variables discussed in this research?"
  },
  {
    title: "Critical analysis",
    question: "What limitations does this research describe?"
  }
];

function SourceList({ sources = [] }) {
  if (!sources.length) return null;

  return (
    <div className="source-section">
      <div className="source-heading">
        <BookOpen size={16} />
        Supporting sources
        <span className="source-count">{sources.length}</span>
      </div>

      <div className="source-list">
        {sources.map((source, index) => (
          <details className="source-card" key={index}>
            <summary>
              <span className="source-index">{index + 1}</span>
              <FileText size={16} className="source-file-icon" />

              <span className="source-file">
                {source.filename || "Document"}
              </span>

              {typeof source.similarity === "number" && (
                <span className="similarity">
                  {(source.similarity * 100).toFixed(0)}% match
                </span>
              )}

              <ChevronDown size={16} className="source-chevron" />
            </summary>

            <div className="source-content">
              {source.text}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function ChatMessage({ message }) {
  const [copied, setCopied] = useState(false);
  const isAI = message.role === "assistant";

  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <article className={`chat-message ${message.role}`}>
      <div className="message-avatar">
        {isAI ? <Sparkles size={18} /> : "You"}
      </div>

      <div className="message-content">
        <div className="message-header">
          <strong>{isAI ? "Knowledge AI" : "You"}</strong>
          <span>{message.time}</span>
        </div>

        <div className="message-body">
          {isAI ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          ) : (
            <p>{message.content}</p>
          )}
        </div>

        {isAI && (
          <>
            <SourceList sources={message.sources} />

            <button
              className="copy-answer"
              type="button"
              onClick={copyAnswer}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? "Copied" : "Copy answer"}
            </button>
          </>
        )}
      </div>
    </article>
  );
}

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);

  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [view, setView] = useState("home");
  const [canForward, setCanForward] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [backendOnline, setBackendOnline] = useState(null);

  const fileInputRef = useRef(null);
  const bottomRef = useRef(null);
  const selectedIdRef = useRef(null);

  const selectedDocument =
    documents.find((doc) => doc.id === selectedId);

  const isReady = selectedDocument?.status === "ready";

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth"
    });
  }, [messages, loading, view]);

  // Restore document library from FastAPI.
  // Continue polling while documents are indexing.
  useEffect(() => {
    let active = true;

    async function refreshDocuments() {
      try {
        const response = await fetch(`${API}/documents`);

        if (!response.ok) {
          throw new Error("Cannot load document library.");
        }

        const data = await response.json();
        if (!active) return;

        const items = data.documents || [];
        setDocuments(items);

        setSelectedId((current) => {
          if (current && items.some((doc) => doc.id === current)) {
            return current;
          }
          return items.find((doc) => doc.status === "ready")?.id ||
            items[0]?.id || null;
        });

        setBackendOnline(true);
      } catch {
        if (active) setBackendOnline(false);
      }
    }

    refreshDocuments();

    const interval = window.setInterval(
      refreshDocuments,
      2000
    );

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  function getTime() {
    return new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit"
    });
  }

  function newChat() {
    setMessages([]);
    setQuestion("");
    setError("");
    setView("home");
    setCanForward(false);
    setSidebarOpen(false);
  }

  function goBack() {
    setView("home");
    setCanForward(messages.length > 0);
  }

  function goForward() {
    if (!canForward || !messages.length) return;
    setView("chat");
  }

  function selectDocument(doc) {
    if (doc.id === selectedId) return;

    setSelectedId(doc.id);
    selectedIdRef.current = doc.id;
    newChat();
  }

  async function uploadPDF(file) {
    if (!file || uploading) return;

    setError("");

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("PDF must be smaller than 10 MB.");
      return;
    }

    setUploading(true);

    try {
      const form = new FormData();
      form.append("file", file);

      const response = await fetch(`${API}/upload`, {
        method: "POST",
        body: form
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Upload failed."
        );
      }

      const newDocument = {
        id: data.document_id,
        filename: data.filename,
        pages: 0,
        chunks: 0,
        status: "queued",
        error: null
      };

      setDocuments((previous) => [
        newDocument,
        ...previous.filter((doc) => doc.id !== newDocument.id)
      ]);

      selectedIdRef.current = newDocument.id;
      setSelectedId(newDocument.id);
      newChat();

    } catch (err) {
      setError(err.message || "PDF upload failed.");
    } finally {
      setUploading(false);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function deleteDocument(doc) {
    if (deletingId || uploading || loading) return;

    const confirmed = window.confirm(
      `Delete "${doc.filename}" and its indexed content?`
    );

    if (!confirmed) return;

    setDeletingId(doc.id);
    setError("");

    try {
      const response = await fetch(
        `${API}/documents/${encodeURIComponent(doc.id)}`,
        { method: "DELETE" }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Delete failed.");
      }

      const remaining = documents.filter(
        (item) => item.id !== doc.id
      );

      setDocuments(remaining);

      if (selectedIdRef.current === doc.id) {
        const nextId = remaining[0]?.id || null;
        selectedIdRef.current = nextId;
        setSelectedId(nextId);
        newChat();
      }

    } catch (err) {
      setError(err.message || "Could not delete document.");
    } finally {
      setDeletingId(null);
    }
  }

  async function sendMessage(event, suggestedQuestion) {
    if (event) event.preventDefault();

    const text = (suggestedQuestion || question).trim();

    if (!text || loading || uploading) return;

    if (!selectedDocument) {
      setError("Upload and select a PDF first.");
      return;
    }

    if (!isReady) {
      setError(
        selectedDocument.status === "failed"
          ? "Indexing failed. Delete and reupload this PDF."
          : "Please wait until indexing is complete."
      );
      return;
    }

    const activeDocumentId = selectedId;
    const activeFilename = selectedDocument.filename;

    setQuestion("");
    setError("");
    setView("chat");
    setCanForward(false);

    setMessages((previous) => [
      ...previous,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        time: getTime()
      }
    ]);

    setLoading(true);

    try {
      const response = await fetch(`${API}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: text,
          top_k: 5,
          document_id: activeDocumentId
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "AI request failed."
        );
      }

      // Never display an answer under the wrong PDF.
      if (selectedIdRef.current !== activeDocumentId) return;

      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.answer || "No answer generated.",
          sources: data.sources || [],
          documentName: data.document_name || activeFilename,
          time: getTime()
        }
      ]);

    } catch (err) {
      if (selectedIdRef.current === activeDocumentId) {
        setError(err.message || "AI request failed.");
      }
    } finally {
      setLoading(false);
    }
  }

  function onDrop(event) {
    event.preventDefault();
    setDragging(false);

    const files = [...event.dataTransfer.files];
    if (files[0]) uploadPDF(files[0]);
  }

  function statusText(doc) {
    if (doc.status === "ready") {
      return `${doc.pages} pages · ${doc.chunks} chunks`;
    }
    if (doc.status === "failed") return "Indexing failed";
    if (doc.status === "indexing") return "Indexing PDF...";
    return "Waiting to index...";
  }

  return (
    <div className={`app ${darkMode ? "dark" : ""}`}>
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-top">
          <div className="brand">
            <div className="brand-logo">
              <BrainCircuit size={24} />
            </div>

            <div className="brand-text">
              <strong>Knowledge AI</strong>
              <span>Enterprise Workspace</span>
            </div>

            <button
              className="icon-button close-sidebar"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close sidebar"
            >
              <X size={20} />
            </button>
          </div>

          <button className="new-chat" onClick={newChat}>
            <Plus size={18} />
            New conversation
          </button>
        </div>

        <div className="sidebar-main">
          <div className="section-title">
            <span>YOUR DOCUMENTS</span>
            <span className="document-count">
              {documents.length}
            </span>
          </div>

          <div
            className={`upload-zone ${dragging ? "dragging" : ""}`}
            onDragEnter={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragOver={(e) => e.preventDefault()}
            onDragLeave={(e) => {
              e.preventDefault();
              setDragging(false);
            }}
            onDrop={onDrop}
          >
            <div className="upload-icon">
              {uploading ? (
                <LoaderCircle className="spin" size={24} />
              ) : (
                <UploadCloud size={24} />
              )}
            </div>

            <strong>
              {uploading ? "Uploading PDF..." : "Add a document"}
            </strong>

            <p>Drop your research paper here</p>

            <button
              className="choose-file"
              type="button"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              Browse files
            </button>

            <small>PDF only · Maximum 10 MB</small>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            hidden
            onChange={(e) => uploadPDF(e.target.files?.[0])}
          />

          <div className="document-list">
            {documents.length === 0 ? (
              <div className="empty-documents">
                <FileText size={20} />
                <p>Your uploaded PDFs will appear here.</p>
              </div>
            ) : (
              documents.map((doc) => (
                <div
                  className={
                    "document-card library-document " +
                    (selectedId === doc.id ? "selected" : "")
                  }
                  key={doc.id}
                >
                  <button
                    type="button"
                    className="document-select"
                    onClick={() => selectDocument(doc)}
                    title={doc.filename}
                  >
                    <div className="document-icon">
                      <FileText size={19} />
                    </div>

                    <div className="document-info">
                      <strong>{doc.filename}</strong>
                      <span>{statusText(doc)}</span>
                    </div>

                    {doc.status === "ready" && (
                      <Check
                        size={15}
                        className="document-check"
                      />
                    )}

                    {["queued", "indexing"].includes(doc.status) && (
                      <LoaderCircle
                        size={15}
                        className="spin indexing-icon"
                      />
                    )}
                  </button>

                  <button
                    type="button"
                    className="document-delete"
                    onClick={() => deleteDocument(doc)}
                    disabled={deletingId !== null || loading}
                    title={`Delete ${doc.filename}`}
                    aria-label={`Delete ${doc.filename}`}
                  >
                    {deletingId === doc.id ? (
                      <LoaderCircle className="spin" size={16} />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="sidebar-bottom">
          <div className="stack-info">
            <Database size={15} />
            <span>LangChain · ChromaDB · FastAPI</span>
          </div>

          <div className="privacy-info">
            <ShieldCheck size={15} />
            <span>Local document library · AI-powered</span>
          </div>
        </div>
      </aside>

      <main className="workspace">
        <header className="header">
          <div className="header-left">
            <button
              className="icon-button mobile-menu"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu size={21} />
            </button>

            <button
              className="icon-button"
              onClick={goBack}
              disabled={view === "home"}
              title="Back to workspace"
              aria-label="Back"
            >
              <ArrowLeft size={20} />
            </button>

            <button
              className="icon-button"
              onClick={goForward}
              disabled={view !== "home" || !canForward}
              title="Forward to conversation"
              aria-label="Forward"
            >
              <ArrowRight size={20} />
            </button>

            <div className="header-titles">
              <h1>Research Assistant</h1>
              <p>
                {selectedDocument
                  ? `Reading: ${selectedDocument.filename}`
                  : "Your documents, intelligently connected."}
              </p>
            </div>
          </div>

          <div className="header-actions">
            <div
              className={
                `connection ${backendOnline === false ? "offline" : ""}`
              }
            >
              <span className="connection-dot" />
              <span>
                {backendOnline === null ? "Checking" :
                 backendOnline ? "Connected" : "Offline"}
              </span>
            </div>

            <button
              className="icon-button"
              onClick={() => setDarkMode(!darkMode)}
              title="Toggle appearance"
              aria-label="Toggle appearance"
            >
              {darkMode ? <Sun size={19} /> : <Moon size={19} />}
            </button>
          </div>
        </header>

        <div className="workspace-content">
          <section className="chat-scroll">
            {view === "home" ? (
              <div className="welcome">
                <div className="welcome-symbol">
                  <Sparkles size={32} />
                </div>

                <span className="eyebrow">
                  YOUR AI RESEARCH WORKSPACE
                </span>

                <h2>
                  Understand your documents.
                  <br />
                  <span>Discover more with AI.</span>
                </h2>

                <p className="welcome-description">
                  Ask questions, explore research and uncover insights
                  from your uploaded documents.
                </p>

                {selectedDocument && (
                  <div className="active-document-banner">
                    <FileText size={19} />

                    <div>
                      <strong>
                        Selected: {selectedDocument.filename}
                      </strong>
                      <span>
                        {selectedDocument.status === "ready"
                          ? "Ready for research questions"
                          : statusText(selectedDocument)}
                      </span>
                    </div>

                    {selectedDocument.status === "ready" ? (
                      <Check size={19} />
                    ) : (
                      <RefreshCw className="spin" size={19} />
                    )}
                  </div>
                )}

                <div className="suggestion-grid">
                  {suggestions.map((item, index) => (
                    <button
                      className="suggestion-card"
                      key={index}
                      onClick={() => sendMessage(null, item.question)}
                      disabled={!isReady || loading}
                    >
                      <span className="suggestion-icon">
                        {index === 0 ? <BookOpen size={19} /> :
                         index === 1 ? <Database size={19} /> :
                         index === 2 ? <Sparkles size={19} /> :
                         <MessageSquare size={19} />}
                      </span>

                      <strong>{item.title}</strong>
                      <span>{item.question}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="messages">
                <div className="chat-document-label">
                  <FileText size={16} />
                  Answers from:
                  <strong>{selectedDocument?.filename}</strong>
                </div>

                {messages.map((message) => (
                  <ChatMessage
                    message={message}
                    key={message.id}
                  />
                ))}

                {loading && (
                  <div className="thinking">
                    <div className="thinking-icon">
                      <LoaderCircle className="spin" size={18} />
                    </div>

                    <div className="thinking-details">
                      <strong>Knowledge AI is analysing</strong>
                      <span>
                        Searching {selectedDocument?.filename}...
                      </span>
                    </div>
                  </div>
                )}

                <div ref={bottomRef} />
              </div>
            )}
          </section>

          <div className="composer-wrapper">
            {error && (
              <div className="error-message" role="alert">
                <AlertCircle size={17} />
                <span>{error}</span>

                <button
                  onClick={() => setError("")}
                  aria-label="Dismiss error"
                >
                  <X size={15} />
                </button>
              </div>
            )}

            <div className="composer-inner">
              <form
                className="composer"
                onSubmit={(e) => sendMessage(e)}
              >
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                  placeholder={
                    !selectedDocument
                      ? "Upload a PDF to begin..."
                      : isReady
                        ? `Ask about ${selectedDocument.filename}...`
                        : "Waiting for document indexing..."
                  }
                  rows={2}
                  disabled={!isReady || loading || uploading}
                  aria-label="Ask a question"
                />

                <div className="composer-bottom">
                  <div className="composer-hint">
                    <Sparkles size={15} />

                    <span>
                      {selectedDocument
                        ? `Using: ${selectedDocument.filename}`
                        : "Select a document"}
                    </span>
                  </div>

                  <button
                    type="submit"
                    className="send-button"
                    disabled={
                      !question.trim() || !isReady ||
                      loading || uploading
                    }
                    aria-label="Send question"
                  >
                    {loading ? (
                      <LoaderCircle className="spin" size={19} />
                    ) : (
                      <Send size={19} />
                    )}
                  </button>
                </div>
              </form>

              <p className="footer-notice">
                AI can make mistakes. Verify important information
                against the original documents.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}