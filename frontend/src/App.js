import React, { useState } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import jsPDF from "jspdf";
import "./App.css";

function App() {
  const [text, setText] = useState("");
  const [summary, setSummary] = useState("");
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState(null);
  const [youtubeURL, setYoutubeURL] = useState("");
  const [thumbnail, setThumbnail] = useState("");
  const [mode, setMode] = useState("text");
  const [loading, setLoading] = useState(false);

  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState("");

  const [table, setTable] = useState("");

  const BASE_URL = "http://127.0.0.1:5000";

  const getVideoId = (url) => {
    try {
      if (url.includes("v=")) {
        return url.split("v=")[1].split("&")[0];
      } else if (url.includes("youtu.be/")) {
        return url.split("youtu.be/")[1].split("?")[0];
      }
    } catch {
      return null;
    }
  };

  const startProgress = () => {
    let value = 0;
    const interval = setInterval(() => {
      value += Math.random() * 10;
      if (value >= 95) {
        value = 95;
        clearInterval(interval);
      }
      setProgress(Math.floor(value));
    }, 300);
    return interval;
  };

  // -------- SUMMARY / TABLE --------
  const handleSummarize = async () => {
    setLoading(true);
    setSummary("");
    setNotes("");
    setTable("");
    setProgress(0);

    let interval;

    try {
      let res;

      if (mode === "text") {
        if (!text.trim()) {
          setLoading(false);
          return alert("Enter text");
        }

        interval = startProgress();

        res = await axios.post(
          `${BASE_URL}/summarize/text`,
          { text },
          {
            headers: {
              "Content-Type": "application/json",
            },
          }
        );

        setSummary(res.data.summary);
      }

      else if (mode === "pdf") {
        if (!file) return alert("Upload PDF");
        interval = startProgress();

        const formData = new FormData();
        formData.append("file", file);

        res = await axios.post(`${BASE_URL}/summarize/pdf`, formData);
        setSummary(res.data.summary);
      }

      else if (mode === "research") {
        if (!file) return alert("Upload PDF");

        setProgressText("📊 Generating research table...");
        interval = startProgress();

        const formData = new FormData();
        formData.append("file", file);

        res = await axios.post(
          `${BASE_URL}/generate/research-table`,
          formData
        );

        setTable(res.data.table);
      }

      else if (mode === "youtube") {
        if (!youtubeURL.trim()) return alert("Enter YouTube URL");

        const vid = getVideoId(youtubeURL);
        if (vid) {
          setThumbnail(`https://img.youtube.com/vi/${vid}/0.jpg`);
        }

        setProgressText("📺 Loading video...");
        interval = startProgress();

        setTimeout(() => {
          setProgressText("📄 Splitting into chunks...");
        }, 1000);

        setTimeout(() => {
          setProgressText("⚡ Generating summary...");
        }, 2000);

        res = await axios.post(`${BASE_URL}/summarize/youtube`, {
          url: youtubeURL,
        });

        setThumbnail(res.data.thumbnail);
        setSummary(res.data.summary);
      }
    } catch (err) {
      console.log("ERROR:", err.response?.data || err.message);
      setSummary("❌ Error occurred");
    } finally {
      clearInterval(interval);
      setProgress(100);
      setLoading(false);
    }
  };

  const handleGenerateNotes = async () => {
    setLoading(true);
    setProgress(0);

    const interval = startProgress();

    try {
      const res = await axios.post(`${BASE_URL}/generate/notes`, {
        summary,
        language: "English",
      });

      setNotes(res.data.notes);
    } catch {
      setNotes("❌ Notes generation failed");
    } finally {
      clearInterval(interval);
      setProgress(100);
      setLoading(false);
    }
  };

  const handleTranslate = async (targetLang) => {
    setLoading(true);

    try {
      const res = await axios.post(`${BASE_URL}/translate`, {
        text: notes || summary,
        target: targetLang,
      });

      if (notes) {
        setNotes(res.data.translated);
      } else {
        setSummary(res.data.translated);
      }
    } catch {
      alert("❌ Translation failed");
    } finally {
      setLoading(false);
    }
  };

  const downloadPDF = () => {
    const doc = new jsPDF();
    const content = notes || summary;

    const lines = doc.splitTextToSize(content, 180);
    doc.text(lines, 10, 10);

    doc.save("notes.pdf");
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">
            <span className="title-icon">🤖</span>
            AI Summarizer Pro
          </h1>
          <p className="app-subtitle">Smart summaries for text, PDF, YouTube & Research</p>
        </div>
      </header>

      {/* Mode Selection */}
      <section className="mode-section">
        <div className="mode-buttons-container">
          <button 
            className={`mode-btn ${mode === 'text' ? 'active' : ''}`}
            onClick={() => setMode("text")}
          >
            📝 Text
          </button>
          <button 
            className={`mode-btn ${mode === 'pdf' ? 'active' : ''}`}
            onClick={() => setMode("pdf")}
          >
            📄 PDF
          </button>
          <button 
            className={`mode-btn ${mode === 'youtube' ? 'active' : ''}`}
            onClick={() => setMode("youtube")}
          >
            🎥 YouTube
          </button>
          <button 
            className={`mode-btn ${mode === 'research' ? 'active' : ''}`}
            onClick={() => setMode("research")}
          >
            📊 Research Paper
          </button>
        </div>
      </section>

      {/* Input Section */}
      <section className="input-section">
        <div className="input-container">
          {mode === "text" && (
            <div className="input-field">
              <label>Paste your text here...</label>
              <textarea
                placeholder="Enter text to summarize..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows="8"
              />
            </div>
          )}

          {(mode === "pdf" || mode === "research") && (
            <div className="input-field">
              <label>Upload PDF file</label>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files[0])}
              />
            </div>
          )}

          {mode === "youtube" && (
            <div className="input-field">
              <label>Paste YouTube URL</label>
              <input
                type="text"
                placeholder="https://www.youtube.com/watch?v=..."
                value={youtubeURL}
                onChange={(e) => setYoutubeURL(e.target.value)}
              />
            </div>
          )}
        </div>

        <button className="summarize-btn" onClick={handleSummarize} disabled={loading}>
          {loading ? (
            <>
              <span className="spinner"></span>
              Processing...
            </>
          ) : (
            "🚀 Generate Summary"
          )}
        </button>
      </section>

      {/* YouTube Thumbnail */}
      {thumbnail && mode === "youtube" && (
        <section className="thumbnail-section">
          <img src={thumbnail} alt="Video thumbnail" className="video-thumbnail" />
        </section>
      )}

      {/* Progress Bar */}
      {loading && (
        <section className="progress-section">
          <div className="progress-card">
            <div className="progress-header">
              <span className="progress-icon">⏳</span>
              <span className="progress-text">Processing your request</span>
            </div>
            <div className="progress-bar-container">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <span className="progress-percentage">{progress}%</span>
            </div>
            <p className="progress-status">{progressText || "Analyzing content..."}</p>
          </div>
        </section>
      )}

      {/* Results Section */}
      <main className="results-section">
        {table && (
          <div className="result-card">
            <div className="result-header">
              <h2>📊 Research Analysis Table</h2>
            </div>
            <div className="result-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {table}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {summary && !notes && (
          <div className="result-card">
            <div className="result-header">
              <h2>✨ AI Summary</h2>
            </div>
            <div className="result-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
            </div>
            <div className="action-buttons">
              <button className="action-btn primary" onClick={handleGenerateNotes}>
                ✍️ Generate Study Notes
              </button>
              <div className="translate-buttons">
                <button className="action-btn" onClick={() => handleTranslate("Bengali")}>
                  🇧🇩 Bengali
                </button>
                <button className="action-btn" onClick={() => handleTranslate("Hindi")}>
                  🇮🇳 Hindi
                </button>
              </div>
            </div>
          </div>
        )}

        {notes && (
          <div className="result-card highlighted">
            <div className="result-header">
              <h2>📚 Study Notes</h2>
            </div>
            <div className="result-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{notes}</ReactMarkdown>
            </div>
            <div className="action-buttons">
              <button className="action-btn primary" onClick={downloadPDF}>
                📥 Download PDF
              </button>
              <div className="translate-buttons">
                <button className="action-btn" onClick={() => handleTranslate("Bengali")}>
                  🇧🇩 Bengali
                </button>
                <button className="action-btn" onClick={() => handleTranslate("Hindi")}>
                  🇮🇳 Hindi
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>Powered by Surjo_AI Summarizer Pro 🚀</p>
      </footer>
    </div>
  );
}

export default App;