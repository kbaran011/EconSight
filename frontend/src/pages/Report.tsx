import { useState } from 'react'
import { downloadReport } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'

export default function Report() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDownload = async () => {
    setLoading(true)
    setError(null)
    try {
      const blob = await downloadReport()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'econsight-report.pdf'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate report')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Economic Report</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Generate PDF Report</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-gray-600">
            Download a comprehensive PDF report combining the executive brief and full econometric analysis,
            including forecasts, health score, and scenario projections.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-blue-50 rounded-lg p-4 text-sm">
              <p className="font-semibold text-blue-800 mb-1">Executive Brief</p>
              <p className="text-blue-600">1-page summary with health score, key indicators, and top risks — designed for client delivery.</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-sm">
              <p className="font-semibold text-gray-700 mb-1">Full Analysis</p>
              <p className="text-gray-500">Complete notebook output with VAR/XGBoost forecasts, SHAP charts, and scenario analysis.</p>
            </div>
          </div>

          <Button onClick={handleDownload} disabled={loading} className="w-full md:w-auto">
            {loading ? 'Generating report…' : 'Download PDF Report'}
          </Button>

          {error && (
            <p className="text-red-500 text-sm">
              {error} — WeasyPrint or nbconvert may not be installed.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
