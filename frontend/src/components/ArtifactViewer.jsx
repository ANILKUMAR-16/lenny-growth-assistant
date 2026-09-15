import React, { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// ── Security badge component ──────────────────────────────────────────────────
function SecurityBadge({ flags, isSanitized }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={`flex flex-col gap-1 security-badge rounded-xl px-3 py-2 ${
      isSanitized ? 'border-amber-500/30 bg-amber-500/10' : ''
    }`} style={!isSanitized ? undefined : {}}>
      <button
        onClick={() => setExpanded(v => !v)}
        className="flex items-center gap-2 w-full text-left"
      >
        {/* Shield icon */}
        <div className={`flex-shrink-0 w-5 h-5 rounded-md flex items-center justify-center ${
          isSanitized ? 'bg-amber-500/20' : 'bg-emerald-500/20'
        }`}>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke={isSanitized ? '#f59e0b' : '#10b981'} strokeWidth="2.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            {isSanitized && <line x1="12" y1="8" x2="12" y2="12"/>}
            {isSanitized && <line x1="12" y1="16" x2="12.01" y2="16"/>}
          </svg>
        </div>

        <div className="flex-1 min-w-0">
          <span className={`text-xs font-semibold ${isSanitized ? 'text-amber-400' : 'text-emerald-400'}`}>
            {isSanitized ? `Sanitized Sandbox Mode` : '✓ Sanitized Sandbox Mode'}
          </span>
          {isSanitized && (
            <span className="text-[10px] text-amber-500/70 ml-1.5">
              ({flags.length} issue{flags.length > 1 ? 's' : ''} removed)
            </span>
          )}
        </div>

        {isSanitized && (
          <svg
            width="12" height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#f59e0b"
            strokeWidth="2"
            className={`transition-transform ${expanded ? 'rotate-180' : ''}`}
          >
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        )}
      </button>

      {/* Expanded flags */}
      {isSanitized && expanded && (
        <div className="mt-1.5 space-y-1 pl-7">
          {flags.map((flag, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[10px] text-amber-500/80">
              <div className="w-1 h-1 rounded-full bg-amber-500" />
              {flag.replace(/_/g, ' ').toLowerCase()}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Tab button ────────────────────────────────────────────────────────────────
function TabButton({ active, onClick, children, id }) {
  return (
    <button
      id={id}
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
        active
          ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30'
          : 'text-slate-400 hover:text-slate-200 hover:bg-surface-600'
      }`}
    >
      {children}
    </button>
  )
}

// ── HTML sandbox iframe ───────────────────────────────────────────────────────
function SandboxedIframe({ content }) {
  const iframeRef = useRef(null)

  useEffect(() => {
    if (!iframeRef.current) return
    const doc = iframeRef.current.contentDocument
    if (!doc) return

    const styledContent = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body {
            font-family: 'Inter', system-ui, sans-serif;
            background: #0a0a0f;
            color: #e2e8f0;
            padding: 24px;
            line-height: 1.6;
            font-size: 14px;
          }
          h1,h2,h3,h4 { color: #f1f5f9; margin-bottom: 12px; margin-top: 20px; font-weight: 600; }
          h1 { font-size: 24px; }
          h2 { font-size: 18px; }
          h3 { font-size: 15px; }
          p { margin-bottom: 12px; color: #cbd5e1; }
          ul, ol { margin: 0 0 12px 20px; color: #cbd5e1; }
          li { margin-bottom: 4px; }
          strong { color: #f1f5f9; font-weight: 600; }
          em { color: #a78bfa; }
          a { color: #818cf8; }
          code { background: #1c1c2e; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
          pre { background: #1c1c2e; padding: 16px; border-radius: 8px; overflow: auto; margin-bottom: 12px; }
          blockquote { border-left: 2px solid #6366f1; padding-left: 16px; color: #94a3b8; margin: 16px 0; }
          hr { border-color: #2a2a42; margin: 20px 0; }
          table { border-collapse: collapse; width: 100%; margin-bottom: 16px; }
          th, td { border: 1px solid #2a2a42; padding: 8px 12px; }
          th { background: #161622; font-weight: 600; }
        </style>
      </head>
      <body>${content}</body>
      </html>
    `

    doc.open()
    doc.write(styledContent)
    doc.close()
  }, [content])

  return (
    <iframe
      ref={iframeRef}
      id="artifact-sandbox-iframe"
      sandbox="allow-scripts"
      title="Sanitized HTML Artifact"
      className="w-full h-full border-0"
      aria-label="Sandboxed HTML preview"
    />
  )
}

// ── Word count badge ──────────────────────────────────────────────────────────
function WordCountBadge({ content }) {
  const count = content.trim().split(/\s+/).filter(Boolean).length
  const target = 1250
  const pct = Math.min(100, Math.round((count / target) * 100))
  const isGood = count >= 1200 && count <= 1300

  return (
    <div className="flex items-center gap-2 text-xs">
      <div className="w-16 h-1.5 bg-surface-500 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isGood ? 'bg-emerald-400' : 'bg-brand-400'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`font-mono ${isGood ? 'text-emerald-400' : 'text-slate-400'}`}>
        {count.toLocaleString()} words
        {isGood && ' ✓'}
      </span>
    </div>
  )
}

// ── Main ArtifactViewer ───────────────────────────────────────────────────────
export default function ArtifactViewer({ artifact, onClose }) {
  const [tab, setTab] = useState('preview') // 'preview' | 'source'
  const [copied, setCopied] = useState(false)

  // Reset to preview tab when artifact changes
  useEffect(() => {
    setTab('preview')
  }, [artifact])

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(artifact.sanitized_content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback: nothing
    }
  }, [artifact.sanitized_content])

  if (!artifact) return null

  const isHtml = artifact.type === 'html'
  const isMarkdown = artifact.type === 'markdown'

  return (
    <div className="flex flex-col h-full bg-surface-800 animate-fade-in">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5 flex-shrink-0">
        {/* Type badge */}
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold ${
          isHtml
            ? 'bg-orange-500/10 text-orange-300 border border-orange-500/20'
            : 'bg-brand-500/10 text-brand-300 border border-brand-500/20'
        }`}>
          {isHtml ? (
            <>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 3h18l-2 14-7 4-7-4L3 3zm4.5 4l1.5 8 3-2 3 2 1.5-8h-9z"/>
              </svg>
              HTML
            </>
          ) : (
            <>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              </svg>
              Markdown
            </>
          )}
        </div>

        <span className="text-slate-400 text-xs truncate flex-1">Artifact</span>

        {/* Tabs */}
        <div className="flex items-center gap-1">
          <TabButton
            id="artifact-tab-preview"
            active={tab === 'preview'}
            onClick={() => setTab('preview')}
          >
            Preview
          </TabButton>
          <TabButton
            id="artifact-tab-source"
            active={tab === 'source'}
            onClick={() => setTab('source')}
          >
            Source
          </TabButton>
        </div>

        {/* Copy */}
        <button
          id="artifact-copy-btn"
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-surface-600 transition-all"
          aria-label="Copy artifact content"
        >
          {copied ? (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          )}
          {copied ? 'Copied!' : 'Copy'}
        </button>

        {/* Close */}
        <button
          id="artifact-close-btn"
          onClick={onClose}
          className="flex items-center justify-center w-7 h-7 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-surface-600 transition-all"
          aria-label="Close artifact panel"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      {/* ── Security badge ──────────────────────────────────────────── */}
      <div className="px-4 py-2.5 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center gap-3 flex-wrap">
          <SecurityBadge
            flags={artifact.security_flags || []}
            isSanitized={artifact.is_sanitized}
          />
          {isMarkdown && (
            <WordCountBadge content={artifact.sanitized_content} />
          )}
        </div>
      </div>

      {/* ── Content area ────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden">
        {tab === 'preview' ? (
          /* Preview */
          isHtml ? (
            <SandboxedIframe content={artifact.sanitized_content} />
          ) : (
            <div
              id="artifact-markdown-preview"
              className="h-full overflow-y-auto px-6 py-5"
            >
              <div className="prose-lenny max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {artifact.sanitized_content}
                </ReactMarkdown>
              </div>
            </div>
          )
        ) : (
          /* Source */
          <div
            id="artifact-source-view"
            className="h-full overflow-auto"
          >
            <pre className="h-full p-5 text-xs font-mono text-slate-300 leading-relaxed bg-surface-900 rounded-none overflow-auto whitespace-pre-wrap break-words">
              <code>{artifact.sanitized_content}</code>
            </pre>
          </div>
        )}
      </div>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <div className="px-4 py-2 border-t border-white/5 flex-shrink-0 flex items-center gap-2">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
        <span className="text-[10px] text-slate-600">
          {isHtml
            ? 'Rendered inside a sandboxed iframe (sandbox="allow-scripts"). Scripts cannot access the parent page.'
            : 'Rendered as sanitized Markdown. All content is client-side only.'}
        </span>
      </div>
    </div>
  )
}
