import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { queryRAG } from '../api/client'
import { Button } from '../components/ui/button'

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

export default function Ask() {
  const [question, setQuestion] = useState('')
  const [submitted, setSubmitted] = useState('')

  const mutation = useMutation({ mutationFn: queryRAG })

  const handleSubmit = (q: string) => {
    const trimmed = q.trim()
    if (!trimmed) return
    setSubmitted(trimmed)
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
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit(question)}
            placeholder="e.g. What is the current inflation trend in Canada?"
            className="flex-1 h-10 rounded-md border border-slate-200 bg-slate-50 px-3 text-[14px] text-slate-800 placeholder:text-slate-400 outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-500 transition"
          />
          <Button
            onClick={() => handleSubmit(question)}
            disabled={mutation.isPending || !question.trim()}
            className="bg-blue-700 hover:bg-blue-800 text-white text-[13px] font-medium px-5 h-10 rounded-md"
          >
            {mutation.isPending ? 'Analysing…' : 'Ask'}
          </Button>
        </div>

        {/* Example chips */}
        <div className="mt-3">
          <p className="text-[11px] text-slate-400 mb-1.5">Try an example</p>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map(q => (
              <button
                key={q}
                onClick={() => { setQuestion(q); handleSubmit(q) }}
                className="text-[12px] text-slate-600 bg-slate-100 hover:bg-blue-50 hover:text-blue-700 border border-slate-200 hover:border-blue-200 rounded-full px-3 py-1 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading state */}
      {mutation.isPending && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center gap-3 text-slate-400 text-sm">
            <span className="flex gap-0.5">
              {[0, 1, 2].map(i => (
                <span key={i} className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: `${i * 0.12}s` }} />
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

      {/* Answer */}
      {mutation.isSuccess && mutation.data && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Question bar */}
          <div className="border-b border-slate-100 px-6 py-4 bg-slate-50">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Question</p>
            <p className="text-[14px] font-medium text-slate-800">{submitted}</p>
          </div>

          {/* Answer body */}
          <div className="px-6 py-5 space-y-5">
            {/* Method tag */}
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full ${
                mutation.data.query_type === 'sql'
                  ? 'bg-violet-50 text-violet-700 border border-violet-200'
                  : 'bg-blue-50 text-blue-700 border border-blue-200'
              }`}>
                <span className="w-1.5 h-1.5 rounded-full bg-current" />
                {METHOD_LABEL[mutation.data.query_type] ?? mutation.data.query_type}
              </span>
            </div>

            {/* Answer text */}
            <div>
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Analysis</p>
              <p className="text-[14px] text-slate-700 leading-relaxed whitespace-pre-wrap">
                {mutation.data.answer}
              </p>
            </div>

            {/* Sources */}
            {mutation.data.sources.length > 0 && (
              <div className="pt-3 border-t border-slate-100">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Sources</p>
                <div className="flex flex-wrap gap-2">
                  {mutation.data.sources.map((s, i) => (
                    <span key={i} className="text-[12px] text-slate-500 bg-slate-50 border border-slate-200 rounded px-2.5 py-1">
                      {s.replace(/¶$/, '').trim()}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
