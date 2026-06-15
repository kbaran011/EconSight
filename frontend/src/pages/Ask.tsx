import { useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { queryRAG } from '../api/client'
import type { RAGResponse } from '../api/client'

interface HistoryEntry {
  question: string
  response: RAGResponse
}

const EXAMPLES = [
  'What is the current inflation trend in Canada?',
  'How has the overnight rate affected the yield spread?',
  'What does the economic health score indicate?',
  'What was the CPI in January 2024?',
]

const METHOD_LABEL: Record<string, string> = {
  sql:       'Live Database Query',
  narrative: 'Semantic Analysis',
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={copy}
      className="text-[11px] font-medium border rounded px-2 py-0.5 transition-colors text-[var(--text-muted)] border-[var(--border)] hover:text-[var(--primary)] hover:border-[var(--primary)]"
    >
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  )
}

function AnswerCard({ entry, index, total }: { entry: HistoryEntry; index: number; total: number }) {
  const { question, response } = entry
  const isLatest = index === total - 1
  return (
    <div className={`ed-card p-5 border-l-[3px] border-l-[var(--primary)] mb-4 ${isLatest ? '' : 'opacity-60'}`}>
      {/* Question bar */}
      <div className="flex items-start justify-between mb-2">
        <p className="font-serif font-semibold text-[16px] text-[var(--text-primary)]">{question}</p>
        <CopyButton text={response.answer} />
      </div>

      {/* Method badge */}
      <span className="inline-flex items-center gap-1.5 bg-[var(--surface-2)] text-[var(--text-muted)] text-[10px] font-mono px-2 py-0.5 rounded">
        {METHOD_LABEL[response.query_type] ?? response.query_type}
      </span>

      {/* Answer */}
      <p className="font-serif text-[15px] text-[var(--text-secondary)] leading-relaxed mt-3 whitespace-pre-wrap">{response.answer}</p>

      {/* Sources */}
      {response.sources.length > 0 && (
        <div className="pt-3 border-t border-[var(--border)] mt-4">
          <p className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">Sources</p>
          <div className="flex flex-wrap gap-1.5">
            {response.sources.map((s, i) => (
              <span key={i} className="bg-[var(--surface-2)] border border-[var(--border)] text-[10px] font-mono text-[var(--text-muted)] px-2 py-0.5 rounded">
                {s.replace(/¶$/, '').trim()}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Ask() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  const mutation = useMutation({
    mutationFn: queryRAG,
    onSuccess: (data, variables) => {
      setHistory(prev => [...prev, { question: variables, response: data }])
      setQuestion('')
      inputRef.current?.focus()
    },
  })

  const handleSubmit = (q: string) => {
    const trimmed = q.trim()
    if (!trimmed || mutation.isPending) return
    mutation.mutate(trimmed)
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <p className="section-label">Intelligence Layer</p>
        <h1 className="text-2xl font-semibold text-slate-900">Ask EconSight</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Query Canadian economic data in natural language. Powered by Llama 3.3 via Groq.
        </p>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <label className="stat-label block mb-2">Your question</label>
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit(question)}
            placeholder="e.g. What is the current inflation trend in Canada?"
            className="bg-white border border-[var(--border)] rounded-lg px-4 py-2.5 text-[14px] font-sans text-[var(--text-primary)] placeholder:text-[var(--text-xmuted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent flex-1"
          />
          <button
            onClick={() => handleSubmit(question)}
            disabled={mutation.isPending || !question.trim()}
            className="bg-[var(--primary)] text-white font-sans font-semibold text-[13px] px-5 py-2.5 rounded-[6px] hover:bg-[var(--primary-dark)] transition-colors disabled:opacity-50"
          >
            {mutation.isPending ? 'Analysing…' : 'Ask'}
          </button>
        </div>

        {/* Example chips */}
        <div className="mt-3">
          <p className="text-[11px] text-[var(--text-muted)] mb-1.5">Try an example</p>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map(q => (
              <button
                key={q}
                onClick={() => { setQuestion(q); handleSubmit(q) }}
                disabled={mutation.isPending}
                className="bg-[var(--surface-2)] border border-[var(--border)] text-[var(--text-secondary)] text-[12px] px-3 py-1.5 rounded-[6px] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-colors cursor-pointer disabled:opacity-40"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading */}
      {mutation.isPending && (
        <div className="bg-white rounded-xl border border-[var(--border)] shadow-sm p-5">
          <div className="flex items-center gap-3 text-[var(--text-secondary)] text-[13px]">
            <span className="flex gap-1">
              {[0, 1, 2].map(i => (
                <span key={i} className="w-2 h-2 rounded-full bg-[var(--primary)] animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
              ))}
            </span>
            Retrieving and analysing economic data…
          </div>
        </div>
      )}

      {/* Error */}
      {mutation.isError && (
        <div className="bg-red-50 rounded-xl border border-red-200 p-5">
          <p className="text-[13px] font-semibold text-red-700">Query Failed</p>
          <p className="text-[13px] text-red-600 mt-1">
            {mutation.error instanceof Error ? mutation.error.message : 'The analysis service is unavailable.'}
          </p>
        </div>
      )}

      {/* Answer history (newest last, older ones dimmed) */}
      {history.length > 0 && (
        <div className="space-y-4">
          {history.map((entry, i) => (
            <AnswerCard key={i} entry={entry} index={i} total={history.length} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {history.length === 0 && !mutation.isPending && !mutation.isError && (
        <div className="text-center py-12 text-[var(--text-muted)]">
          <p className="text-[32px] mb-2">💬</p>
          <p className="text-[14px]">Ask a question above to get started</p>
        </div>
      )}
    </div>
  )
}
