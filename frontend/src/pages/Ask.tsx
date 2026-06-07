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
      className="text-[11px] font-medium text-slate-400 hover:text-slate-700 border border-slate-200 rounded px-2 py-0.5 transition-colors"
    >
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  )
}

function AnswerCard({ entry, index, total }: { entry: HistoryEntry; index: number; total: number }) {
  const { question, response } = entry
  const isLatest = index === total - 1
  return (
    <div className={`bg-white rounded-xl border shadow-sm overflow-hidden transition-opacity ${isLatest ? 'border-blue-200' : 'border-slate-200 opacity-60'}`}>
      {/* Question bar */}
      <div className={`px-6 py-3.5 border-b flex items-center justify-between ${isLatest ? 'bg-blue-50 border-blue-100' : 'bg-slate-50 border-slate-100'}`}>
        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">Question</p>
          <p className="text-[14px] font-medium text-slate-800">{question}</p>
        </div>
        <CopyButton text={response.answer} />
      </div>

      {/* Body */}
      <div className="px-6 py-5 space-y-4">
        {/* Method */}
        <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full border ${
          response.query_type === 'sql'
            ? 'bg-violet-50 text-violet-700 border-violet-200'
            : 'bg-blue-50 text-blue-700 border-blue-200'
        }`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {METHOD_LABEL[response.query_type] ?? response.query_type}
        </span>

        {/* Answer */}
        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Analysis</p>
          <p className="text-[14px] text-slate-700 leading-relaxed whitespace-pre-wrap">{response.answer}</p>
        </div>

        {/* Sources */}
        {response.sources.length > 0 && (
          <div className="pt-3 border-t border-slate-100">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Sources</p>
            <div className="flex flex-wrap gap-1.5">
              {response.sources.map((s, i) => (
                <span key={i} className="text-[12px] text-slate-500 bg-slate-50 border border-slate-200 rounded px-2.5 py-1">
                  {s.replace(/¶$/, '').trim()}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
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
        <p className="section-title">Intelligence Layer</p>
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
            className="flex-1 h-10 rounded-md border border-slate-200 bg-slate-50 px-3 text-[14px] text-slate-800 placeholder:text-slate-400 outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-500 transition"
          />
          <button
            onClick={() => handleSubmit(question)}
            disabled={mutation.isPending || !question.trim()}
            className="bg-blue-700 hover:bg-blue-800 disabled:bg-blue-300 text-white text-[13px] font-medium px-5 h-10 rounded-md transition-colors"
          >
            {mutation.isPending ? 'Analysing…' : 'Ask'}
          </button>
        </div>

        {/* Example chips */}
        <div className="mt-3">
          <p className="text-[11px] text-slate-400 mb-1.5">Try an example</p>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map(q => (
              <button
                key={q}
                onClick={() => { setQuestion(q); handleSubmit(q) }}
                disabled={mutation.isPending}
                className="text-[12px] text-slate-600 bg-slate-100 hover:bg-blue-50 hover:text-blue-700 border border-slate-200 hover:border-blue-200 rounded-full px-3 py-1 transition-colors disabled:opacity-40"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading */}
      {mutation.isPending && (
        <div className="bg-white rounded-xl border border-blue-100 shadow-sm p-5">
          <div className="flex items-center gap-3 text-slate-500 text-[13px]">
            <span className="flex gap-1">
              {[0, 1, 2].map(i => (
                <span key={i} className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
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
        <div className="text-center py-12 text-slate-400">
          <p className="text-[32px] mb-2">💬</p>
          <p className="text-[14px]">Ask a question above to get started</p>
        </div>
      )}
    </div>
  )
}
