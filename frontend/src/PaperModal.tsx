import React from "react";
import { Paper } from "./types";

interface Props {
  paper: Paper | null;
  onClose: () => void;
}

const PaperModal: React.FC<Props> = ({ paper, onClose }) => {
  if (!paper) return null;

  const authors = parseAuthors(paper.author);

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        {/* Close button */}
        <button style={closeButtonStyle} onClick={onClose}>
          close
        </button>

        <h2 style={titleStyle}>Paper Details</h2>

        <div style={contentStyle}>
          <Row label="SID" value={paper.SID} />
          <Row label="Title" value={stripQuotes(paper.title)} />

          {/* Authors as "given family (affiliation)" list */}
          {authors.length > 0 && (
            <div style={{ marginBottom: "1rem" }}>
              <div style={labelStyle}>Authors</div>
              <ul style={authorListStyle}>
                {authors.map((a, idx) => (
                  <li key={idx}>
                    {a.name}
                    {a.affiliation && (
                      <span style={{ color: "#555" }}> ({a.affiliation})</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <Row label="Journal" value={stripQuotes(paper.container_title)} />
          <Row label="Volume" value={stripQuotes(paper.volume)} />
          <Row label="Issue" value={stripQuotes(paper.issue)} />
          <Row label="Pages" value={formatPages(paper.page)} />
          <Row label="Publication Date" value={formatIssuedDate(paper.issued)} />
          <Row label="DOI" value={paper.DOI} />

          {paper.URL && (
            <div style={{ marginBottom: "1rem" }}>
              <div style={labelStyle}>URL</div>
              <a
                href={paper.URL}
                target="_blank"
                rel="noreferrer"
                style={urlStyle}
              >
                {paper.URL}
              </a>
            </div>
          )}

          <Row label="Publisher" value={paper.publisher} />
          <Row label="Project Names" value={formatProjectNames(paper.project_names)} />
        </div>
      </div>
    </div>
  );
};

export default PaperModal;

/* ------------------------------ */
/*  Helpers                       */
/* ------------------------------ */

// Parse authors like:
// "Taro Yamada (Tokyo Univ.), Hanako Suzuki (NIMS)"
// => [{name: "Taro Yamada", affiliation: "Tokyo Univ."}, ...]
function parseAuthors(raw: string | null): { name: string; affiliation?: string }[] {
  if (!raw) return [];

  let jsonData: any = null;

  // Try to parse JSON array
  try {
    jsonData = JSON.parse(raw);
  } catch {
    // fallback: treat as text
  }

  // Case 1: JSON array format
  if (Array.isArray(jsonData)) {
    return jsonData.map((a: any) => {
      const given = a.given ?? "";
      const family = a.family ?? "";
      const name = `${given} ${family}`.trim();

      let aff = "";
      if (Array.isArray(a.affiliation) && a.affiliation.length > 0) {
        // Example format: { name: "MIT" }
        aff = a.affiliation.map((x: any) => x.name ?? "").join(", ");
      }

      return aff ? { name, affiliation: aff } : { name };
    });
  }

  // Case 2: old-style string fallback
  return raw
    .split(/[,;]+/)
    .map((s) => s.trim())
    .filter((s) => s)
    .map((part) => ({ name: part }));
}

// Publication Dateの整形
function formatIssuedDate(raw: string | null): string | null {
  if (!raw) return null;

  try {
    const obj = JSON.parse(raw);

    if (
      obj.date_parts &&
      Array.isArray(obj.date_parts) &&
      Array.isArray(obj.date_parts[0])
    ) {
      const [y, m, d] = obj.date_parts[0];
      if (y && m && d) return `${y}/${m}/${d}`;
      if (y && m) return `${y}/${m}`;
      if (y) return `${y}`;
    }
  } catch {
    // JSONでない場合はそのまま返す
  }

  return raw;
}

// Project Namesの整形
function formatProjectNames(raw: string | null): string | null {
  if (!raw) return null;

  try {
    const arr = JSON.parse(raw);
    if (Array.isArray(arr)) {
      return arr.join(", ");
    }
  } catch {
    // raw が JSON ではない場合はそのまま
  }
  return raw;
}

// ダブルクォーテーションの削除
function stripQuotes(v: string | null | undefined): string | null {
  if (!v) return null;
  return v.replace(/^"(.*)"$/, "$1");
}

// Pagesの整形
function formatPages(v: string | null | undefined): string | null {
  const cleaned = stripQuotes(v);
  if (!cleaned) return null;
  return `pp. ${cleaned}`;
}

const Row = ({ label, value }: { label: string; value?: string | null }) => {
  if (!value) return null;
  return (
    <div style={{ marginBottom: "1rem" }}>
      <div style={labelStyle}>{label}</div>
      <div style={valueStyle}>{value}</div>
    </div>
  );
};

/* ------------------------------ */
/* Styles                         */
/* ------------------------------ */

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(0,0,0,0.45)",
  backdropFilter: "blur(4px)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 2000,
};

const modalStyle: React.CSSProperties = {
  background: "rgba(255, 255, 255, 0.95)",
  borderRadius: "16px",
  padding: "2rem",
  width: "90%",
  maxWidth: "650px",
  boxShadow: "0 8px 30px rgba(0,0,0,0.25)",
  position: "relative",
};

const closeButtonStyle: React.CSSProperties = {
  position: "absolute",
  top: "12px",
  right: "12px",
  border: "none",
  background: "transparent",
  fontSize: "1.5rem",
  cursor: "pointer",
  color: "#666",
};

const titleStyle: React.CSSProperties = {
  marginBottom: "1.5rem",
  fontSize: "1.6rem",
  fontWeight: 700,
  textAlign: "center",
  color: "#333",
};

const labelStyle: React.CSSProperties = {
  fontSize: "0.9rem",
  color: "#555",
  fontWeight: 600,
  marginBottom: "0.25rem",
};

const valueStyle: React.CSSProperties = {
  fontSize: "1.05rem",
  color: "#222",
  paddingLeft: "0.3rem",
  lineHeight: 1.5,
};

const urlStyle: React.CSSProperties = {
  color: "#0066cc",
  wordBreak: "break-all",
  textDecoration: "underline",
  fontSize: "1rem",
};

const authorListStyle: React.CSSProperties = {
  paddingLeft: "1.25rem",
  marginTop: "0.25rem",
  lineHeight: 1.5,
};

const contentStyle: React.CSSProperties = {
  maxHeight: "70vh",
  overflowY: "auto",
  paddingRight: "0.5rem",
};
