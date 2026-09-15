import React, { useState, useCallback } from 'react'
import ChatInterface from './components/ChatInterface'
import ArtifactViewer from './components/ArtifactViewer'

export default function App() {
  const [artifact, setArtifact] = useState(null)
  const [artifactVisible, setArtifactVisible] = useState(false)

  const handleArtifact = useCallback((newArtifact) => {
    if (newArtifact && newArtifact.type !== 'none') {
      setArtifact(newArtifact)
      setArtifactVisible(true)
    }
  }, [])

  const handleCloseArtifact = useCallback(() => {
    setArtifactVisible(false)
    setTimeout(() => setArtifact(null), 300)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      {/* ── Header bar ───────────────────────────────────────────────── */}
      <div className="fixed top-0 left-0 right-0 z-50 h-14 glass border-b border-white/5 flex items-center px-6 gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-brand flex items-center justify-center shadow-glow-sm">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div>
            <span className="font-bold text-sm text-white tracking-tight">Lenny</span>
            <span className="text-brand-400 font-bold text-sm tracking-tight"> Growth</span>
            <span className="text-slate-400 text-xs ml-1 hidden sm:inline">by Oogway Labs</span>
          </div>
        </div>

        {/* Status pill */}
        <div className="flex items-center gap-1.5 ml-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-slow" />
          <span className="text-emerald-400 text-xs font-medium">RAG Active</span>
        </div>

        <div className="flex-1" />

        {/* Artifact toggle */}
        {artifact && (
          <button
            id="artifact-panel-toggle"
            onClick={() => setArtifactVisible(v => !v)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg glass border border-brand-500/30 text-brand-300 text-sm font-medium hover:border-brand-500/60 hover:bg-brand-500/10 transition-all"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M9 3v18M3 9h6"/>
            </svg>
            {artifactVisible ? 'Hide Artifact' : 'Show Artifact'}
          </button>
        )}

        {/* Docs link */}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 text-sm transition-colors hover:bg-surface-600"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          API Docs
        </a>
      </div>

      {/* ── Main layout ──────────────────────────────────────────────── */}
      <div className="flex w-full pt-14 overflow-hidden">
        {/* Chat panel */}
        <div
          className={`flex-1 min-w-0 transition-all duration-300 ease-out ${
            artifactVisible ? 'hidden sm:flex sm:flex-col' : 'flex flex-col'
          }`}
          style={artifactVisible ? { maxWidth: '50%' } : {}}
        >
          <ChatInterface onArtifact={handleArtifact} />
        </div>

        {/* Artifact panel */}
        <div
          className={`transition-all duration-300 ease-out overflow-hidden ${
            artifactVisible
              ? 'w-full sm:w-1/2 flex flex-col border-l border-white/5'
              : 'w-0'
          }`}
        >
          {artifact && (
            <ArtifactViewer
              artifact={artifact}
              onClose={handleCloseArtifact}
            />
          )}
        </div>
      </div>
    </div>
  )
}
