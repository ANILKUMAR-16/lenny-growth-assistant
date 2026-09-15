import React, { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import axios from 'axios'
import { v4 as uuidv4 } from 'uuid'

const API_BASE = '/api'

const PROVIDERS = [
  { value: 'ollama', label: 'Local Ollama', icon: '🦙', desc: 'llama3.2 · private' },
  { value: 'anthropic', label: 'Claude (Anthropic)', icon: '🌩', desc: 'cloud · fast' },
  { value: 'openai', label: 'GPT-4o (OpenAI)', icon: '⚡', desc: 'cloud · capable' },
]

const SUGGESTED_PROMPTS = [
  { text: 'How did Airbnb achieve product-market fit?', icon: '🚀' },
  { text: 'Explain the North Star Metric framework', icon: '⭐' },
  { text: 'What makes referral programs work?', icon: '🔄' },
  { text: 'Write a Ship 30 essay on growth loops', icon: '✍️', isShip30: true },
]

// ── Typing indicator ──────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3">
      <div className="flex items-center gap-1 px-3 py-2 glass rounded-2xl rounded-bl-sm">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    </div>
  )
}

// ── Citation badge ────────────────────────────────────────────────────────────
function CitationBadge({ citation }) {
  return (
    <a
      href={citation.source_url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs hover:bg-brand-500/20 hover:border-brand-500/40 transition-all cursor-pointer"
      title={`Similarity: ${(citation.score * 100).toFixed(0)}%`}
    >
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
      </svg>
      [{citation.index}] {citation.transcript_title.split(':')[0].substring(0, 32)}
      <span className="text-brand-500/60">· {(citation.score * 100).toFixed(0)}%</span>
    </a>
  )
}

// ── Message bubble ────────────────────────────────────────────────────────────
function MessageBubble({ message, onViewArtifact }) {
  const isUser = message.role === 'user'
  const hasArtifact = message.artifact && message.artifact.type !== 'none'

  return (
    <div className={`flex gap-3 message-enter ${isUser ? 'flex-row-reverse' : 'flex-row'} group`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
        isUser
          ? 'bg-brand-600 text-white'
          : 'bg-gradient-to-br from-violet-600 to-indigo-700 text-white shadow-glow-sm'
      }`}>
        {isUser ? 'U' : 'L'}
      </div>

      {/* Content */}
      <div className={`flex-1 min-w-0 max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <div className={`px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-brand-600 text-white rounded-br-sm ml-auto'
            : 'glass rounded-bl-sm'
        }`}>
          {isUser ? (
            <p className="text-sm leading-relaxed">{message.content}</p>
          ) : (
            <div className="prose-lenny text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1 pl-1">
            {message.citations.map((c) => (
              <CitationBadge key={c.index} citation={c} />
            ))}
          </div>
        )}

        {/* Artifact button */}
        {!isUser && hasArtifact && (
          <button
            id={`view-artifact-${message.id}`}
            onClick={() => onViewArtifact(message.artifact)}
            className="flex items-center gap-2 mt-1.5 ml-1 px-3 py-1.5 rounded-lg border border-accent-500/30 bg-accent-500/10 text-accent-300 text-xs font-medium hover:border-accent-500/60 hover:bg-accent-500/20 transition-all"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
            View {message.artifact.type === 'html' ? 'HTML' : 'Markdown'} Artifact
            {message.artifact.security_flags?.length > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 text-[10px]">
                {message.artifact.security_flags.length} issue{message.artifact.security_flags.length > 1 ? 's' : ''} fixed
              </span>
            )}
          </button>
        )}

        {/* Meta: provider + time */}
        {!isUser && message.provider_used && (
          <div className="flex items-center gap-2 pl-1 mt-0.5">
            <span className="text-[10px] text-slate-600">
              {PROVIDERS.find(p => p.value === message.provider_used)?.icon}{' '}
              {message.provider_used}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Ship 30 modal ─────────────────────────────────────────────────────────────
function Ship30Modal({ isOpen, onClose, onSubmit, isLoading }) {
  const [topic, setTopic] = useState('')
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative glass-bright rounded-2xl p-6 w-full max-w-md shadow-glass animate-slide-up">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gold-400 to-orange-500 flex items-center justify-center">
            <span className="text-lg">✍️</span>
          </div>
          <div>
            <h2 className="text-white font-bold text-base">Ship 30 for 30 Essay</h2>
            <p className="text-slate-400 text-xs">~1,250 words · grounded in Lenny's transcripts</p>
          </div>
        </div>

        <label className="block text-slate-300 text-sm font-medium mb-2">Essay Topic</label>
        <textarea
          id="ship30-topic-input"
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="e.g. How referral programs create compounding growth..."
          rows={3}
          className="w-full bg-surface-700 border border-white/10 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-500 resize-none focus:outline-none focus:border-brand-500/60 transition-colors"
        />

        <div className="flex gap-3 mt-4">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-white/10 text-slate-400 text-sm hover:bg-surface-600 transition-colors"
          >
            Cancel
          </button>
          <button
            id="ship30-generate-btn"
            onClick={() => { if (topic.trim()) { onSubmit(topic.trim()); setTopic('') } }}
            disabled={!topic.trim() || isLoading}
            className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-gold-500 to-orange-500 text-white text-sm font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isLoading ? 'Generating…' : 'Generate Essay'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main ChatInterface ────────────────────────────────────────────────────────
export default function ChatInterface({ onArtifact }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [provider, setProvider] = useState('ollama')
  const [error, setError] = useState(null)
  const [showShip30, setShowShip30] = useState(false)
  const [isShip30Loading, setIsShip30Loading] = useState(false)
  const [providerOpen, setProviderOpen] = useState(false)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const messagesContainerRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isLoading) return

    const userMessage = {
      id: uuidv4(),
      role: 'user',
      content: text.trim(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setError(null)

    try {
      const response = await axios.post(`${API_BASE}/chat`, {
        message: text.trim(),
        session_id: sessionId,
        model_provider: provider,
      })

      const data = response.data
      if (!sessionId) setSessionId(data.session_id)

      const assistantMessage = {
        id: data.message_id,
        role: 'assistant',
        content: data.content,
        citations: data.citations,
        artifact: data.artifact,
        provider_used: data.provider_used,
      }

      setMessages(prev => [...prev, assistantMessage])

      if (data.artifact && data.artifact.type !== 'none') {
        onArtifact(data.artifact)
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'An error occurred'
      setError(detail)
      setMessages(prev => [...prev, {
        id: uuidv4(),
        role: 'assistant',
        content: `⚠️ **Error**: ${detail}`,
        citations: [],
        artifact: { type: 'none' },
      }])
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, sessionId, provider, onArtifact])

  const handleShip30Submit = useCallback(async (topic) => {
    setShowShip30(false)
    setIsShip30Loading(true)
    setError(null)

    const userMessage = {
      id: uuidv4(),
      role: 'user',
      content: `✍️ **Ship 30 Essay Request**: ${topic}`,
    }
    setMessages(prev => [...prev, userMessage])

    try {
      const response = await axios.post(`${API_BASE}/skills/ship30`, {
        topic,
        session_id: sessionId,
        model_provider: provider,
      })
      const data = response.data
      if (!sessionId) setSessionId(data.session_id)

      const wordCount = data.word_count
      const assistantMessage = {
        id: uuidv4(),
        role: 'assistant',
        content: data.essay,
        citations: data.citations,
        artifact: { type: 'markdown', sanitized_content: data.essay, security_flags: [], is_sanitized: false },
        provider_used: data.provider_used,
        meta: `Ship 30 essay · ${wordCount} words`,
      }
      setMessages(prev => [...prev, assistantMessage])
      onArtifact(assistantMessage.artifact)
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setError(detail)
    } finally {
      setIsShip30Loading(false)
    }
  }, [sessionId, provider, onArtifact])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const selectedProvider = PROVIDERS.find(p => p.value === provider)
  const isAnyLoading = isLoading || isShip30Loading

  return (
    <>
      <Ship30Modal
        isOpen={showShip30}
        onClose={() => setShowShip30(false)}
        onSubmit={handleShip30Submit}
        isLoading={isShip30Loading}
      />

      <div className="flex flex-col h-full">
        {/* ── Messages area ──────────────────────────────────────────── */}
        <div
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto px-4 py-4 space-y-5"
        >
          {/* Empty state */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px] animate-fade-in">
              {/* Hero */}
              <div className="relative mb-6">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-500 to-accent-600 flex items-center justify-center shadow-glow-brand">
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                </div>
                <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-emerald-400 border-2 border-surface-900 flex items-center justify-center">
                  <svg width="8" height="8" viewBox="0 0 24 24" fill="white">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                  </svg>
                </div>
              </div>

              <h1 className="text-2xl font-bold text-white mb-2">
                Lenny <span className="text-gradient">Growth Assistant</span>
              </h1>
              <p className="text-slate-400 text-sm text-center max-w-xs mb-8">
                Ask growth questions grounded in Lenny's podcast transcripts.
                Generate Ship 30 essays. Explore product strategy.
              </p>

              {/* Suggested prompts */}
              <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
                {SUGGESTED_PROMPTS.map((prompt, i) => (
                  <button
                    key={i}
                    id={`suggested-prompt-${i}`}
                    onClick={() => prompt.isShip30 ? setShowShip30(true) : sendMessage(prompt.text)}
                    className="flex items-center gap-3 px-4 py-3 glass rounded-xl border border-white/5 text-left hover:border-brand-500/30 hover:bg-brand-500/5 transition-all group text-sm text-slate-300 hover:text-white"
                  >
                    <span className="text-base">{prompt.icon}</span>
                    <span className="flex-1">{prompt.text}</span>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="opacity-0 group-hover:opacity-100 text-brand-400 transition-opacity">
                      <path d="M5 12h14M12 5l7 7-7 7"/>
                    </svg>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onViewArtifact={onArtifact}
            />
          ))}

          {/* Typing indicator */}
          {isAnyLoading && <TypingIndicator />}

          <div ref={messagesEndRef} />
        </div>

        {/* ── Error banner ────────────────────────────────────────────── */}
        {error && (
          <div className="mx-4 mb-2 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs flex items-center gap-2 animate-fade-in">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-200">✕</button>
          </div>
        )}

        {/* ── Input area ──────────────────────────────────────────────── */}
        <div className="px-4 pb-4">
          {/* Session info */}
          {sessionId && (
            <div className="flex items-center gap-2 mb-2 px-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-[10px] text-slate-500 font-mono">
                Session: {sessionId.substring(0, 8)}…
              </span>
              <button
                id="new-session-btn"
                onClick={() => { setSessionId(null); setMessages([]) }}
                className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors ml-1"
              >
                New session
              </button>
            </div>
          )}

          <div className="glass-bright rounded-2xl p-3 shadow-glass">
            <textarea
              id="chat-input"
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about growth strategy, PLG, referrals… (Enter to send)"
              rows={2}
              disabled={isAnyLoading}
              className="w-full bg-transparent text-sm text-slate-200 placeholder-slate-500 resize-none focus:outline-none leading-relaxed disabled:opacity-50"
            />

            {/* Controls row */}
            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/5">
              {/* Provider selector */}
              <div className="relative">
                <button
                  id="provider-selector-btn"
                  onClick={() => setProviderOpen(v => !v)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg glass border border-white/10 text-xs text-slate-300 hover:border-brand-500/40 transition-all"
                >
                  <span>{selectedProvider?.icon}</span>
                  <span className="hidden sm:inline">{selectedProvider?.label}</span>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                </button>

                {providerOpen && (
                  <div className="absolute bottom-full left-0 mb-2 w-52 glass-bright rounded-xl border border-white/10 shadow-glass overflow-hidden z-10 animate-slide-up">
                    {PROVIDERS.map(p => (
                      <button
                        key={p.value}
                        id={`provider-option-${p.value}`}
                        onClick={() => { setProvider(p.value); setProviderOpen(false) }}
                        className={`flex items-center gap-3 w-full px-4 py-3 text-left hover:bg-brand-500/10 transition-colors ${
                          provider === p.value ? 'bg-brand-500/15 text-brand-300' : 'text-slate-300'
                        }`}
                      >
                        <span className="text-base">{p.icon}</span>
                        <div>
                          <div className="text-sm font-medium leading-tight">{p.label}</div>
                          <div className="text-[10px] text-slate-500">{p.desc}</div>
                        </div>
                        {provider === p.value && (
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="ml-auto">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                          </svg>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Ship 30 button */}
              <button
                id="ship30-open-btn"
                onClick={() => setShowShip30(true)}
                disabled={isAnyLoading}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-gold-400 hover:bg-gold-500/10 border border-transparent hover:border-gold-500/20 transition-all disabled:opacity-40"
              >
                ✍️ <span className="hidden sm:inline">Ship 30</span>
              </button>

              <div className="flex-1" />

              {/* Character count */}
              {input.length > 0 && (
                <span className={`text-[10px] ${input.length > 3800 ? 'text-red-400' : 'text-slate-500'}`}>
                  {input.length}/4096
                </span>
              )}

              {/* Send button */}
              <button
                id="send-message-btn"
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isAnyLoading}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-glow-sm hover:shadow-glow-brand"
              >
                {isAnyLoading ? (
                  <>
                    <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                    </svg>
                    <span className="hidden sm:inline">Thinking</span>
                  </>
                ) : (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                    <span className="hidden sm:inline">Send</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
