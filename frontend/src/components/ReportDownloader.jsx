import { FileJson, FileSpreadsheet, FileText } from 'lucide-react'

export default function ReportDownloader({
  analysisData,
  filename = 'document',
}) {
  if (!analysisData) return null

  const baseName = filename.replace(/\.[^/.]+$/, '')

  const downloadJson = () => {
    // Zero raw PII in downloaded report: uses sanitized response
    const exportPayload = {
      audit_request_id: analysisData.request_id,
      timestamp: new Date().toISOString(),
      filename: analysisData.filename,
      file_type: analysisData.file_type,
      detected_languages: analysisData.detected_languages,
      primary_language: analysisData.primary_language,
      is_mixed_language: analysisData.is_mixed_language,
      overall_risk: analysisData.overall_risk,
      risk_score: analysisData.risk_score,
      risk_factors: analysisData.risk_factors,
      sanitized_text: analysisData.sanitized_text,
      entities: analysisData.entities,
      entity_counts: analysisData.entity_counts,
      validation_summary: analysisData.validation_summary,
      validation_findings: analysisData.validation_findings,
      llm_analysis: analysisData.llm_analysis,
      metrics: analysisData.metrics,
    }

    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `DPDP_Audit_Report_${baseName}_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadCsv = () => {
    const findings = analysisData.validation_findings || []
    if (findings.length === 0) return

    const headers = ['Category', 'Severity', 'Location', 'Field', 'Masked Value', 'Explanation', 'Suggestion', 'Confidence']
    const rows = findings.map((f) => [
      f.category,
      f.severity,
      `"${(f.location || '').replace(/"/g, '""')}"`,
      `"${(f.field || '').replace(/"/g, '""')}"`,
      `"${(f.masked_value || '').replace(/"/g, '""')}"`,
      `"${(f.explanation || '').replace(/"/g, '""')}"`,
      `"${(f.suggestion || '').replace(/"/g, '""')}"`,
      f.confidence,
    ])

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Validation_Findings_${baseName}_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadSanitizedText = () => {
    const text = analysisData.sanitized_text || ''
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Sanitized_${baseName}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <button
        type="button"
        onClick={downloadJson}
        className="inline-flex items-center gap-1.5 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 shadow-sm hover:bg-blue-100"
      >
        <FileJson className="h-4 w-4" />
        Audit Report (JSON)
      </button>

      <button
        type="button"
        onClick={downloadCsv}
        disabled={!analysisData.validation_findings?.length}
        className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700 shadow-sm hover:bg-emerald-100 disabled:opacity-40"
      >
        <FileSpreadsheet className="h-4 w-4" />
        Findings (CSV)
      </button>

      <button
        type="button"
        onClick={downloadSanitizedText}
        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-100"
      >
        <FileText className="h-4 w-4" />
        Sanitized Text (TXT)
      </button>
    </div>
  )
}
