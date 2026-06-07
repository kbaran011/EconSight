import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { queryRAG } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'

const EXAMPLE_QUESTIONS = [
  'What is the current inflation trend in Canada?',
  'How has the overnight rate affected the yield spread?',
  'What does the economic health score indicate?',
]

export default function Ask() {
  const [question, setQuestion] = useState('')
  const [submitted, setSubmitted] = useState('')

  const mutation = useMutation({ mutationFn: queryRAG })

  const handleSubmit = (q: string) => {
    if (!q.trim()) return
    setSubmitted(q)
    mutation.mutate(q)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Ask EconSight</h1>
      <p className="text-sm text-gray-500">Ask a natural language question about Canadian economic conditions.</p>

      <Card>
        <CardContent className="pt-5">
          <div className="flex gap-2">
            <Input
              placeholder="e.g. What is the current inflation trend?"
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit(question)}
              className="flex-1"
            />
            <Button onClick={() => handleSubmit(question)} disabled={mutation.isPending || !question.trim()}>
              {mutation.isPending ? 'Thinking…' : 'Ask'}
            </Button>
          </div>

          <div className="flex flex-wrap gap-2 mt-3">
            {EXAMPLE_QUESTIONS.map(q => (
              <button
                key={q}
                onClick={() => { setQuestion(q); handleSubmit(q) }}
                className="text-xs text-blue-600 hover:text-blue-800 underline underline-offset-2"
              >
                {q}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {mutation.isPending && (
        <Card>
          <CardContent className="pt-5">
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <span className="animate-pulse">●</span> Searching economic data…
            </div>
          </CardContent>
        </Card>
      )}

      {mutation.isError && (
        <Card className="border-red-200">
          <CardContent className="pt-5">
            <p className="text-red-600 text-sm font-medium">Query failed</p>
            <p className="text-red-500 text-xs mt-1">
              {mutation.error instanceof Error ? mutation.error.message : 'The RAG service may be unavailable (check ANTHROPIC_API_KEY in .env).'}
            </p>
          </CardContent>
        </Card>
      )}

      {mutation.isSuccess && mutation.data && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-500">Q: {submitted}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <Badge variant={mutation.data.query_type === 'sql' ? 'default' : 'secondary'}>
                {mutation.data.query_type}
              </Badge>
            </div>
            <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">{mutation.data.answer}</p>
            {mutation.data.sources.length > 0 && (
              <div>
                <p className="text-xs text-gray-400 mb-1">Sources</p>
                <ul className="space-y-1">
                  {mutation.data.sources.map((s, i) => (
                    <li key={i} className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1">{s}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
