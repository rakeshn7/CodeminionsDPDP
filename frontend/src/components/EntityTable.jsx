export default function EntityTable({ entities = [] }) {
  const colorMap = {
    PERSON: 'bg-sky-50 text-sky-800 border-sky-200',
    AADHAAR: 'bg-purple-50 text-purple-800 border-purple-200',
    PAN: 'bg-cyan-50 text-cyan-800 border-cyan-200',
    ADDRESS: 'bg-amber-50 text-amber-800 border-amber-200',
    GSTIN: 'bg-rose-50 text-rose-800 border-rose-200',
    VOTER_ID: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    PASSPORT: 'bg-pink-50 text-pink-800 border-pink-200',
    PHONE_NUMBER: 'bg-indigo-50 text-indigo-800 border-indigo-200',
    EMAIL_ADDRESS: 'bg-teal-50 text-teal-800 border-teal-200',
    BANK_ACCOUNT: 'bg-blue-50 text-blue-800 border-blue-200',
    DATE_OF_BIRTH: 'bg-orange-50 text-orange-800 border-orange-200',
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-900">Detected Entity Map</h3>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-semibold text-slate-700">{entities.length} entries</span>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-50 text-slate-700">
            <tr>
              <th className="px-4 py-3 font-semibold text-xs uppercase tracking-wider">Entity type</th>
              <th className="px-4 py-3 font-semibold text-xs uppercase tracking-wider">Character offsets</th>
              <th className="px-4 py-3 font-semibold text-xs uppercase tracking-wider">Source / confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white text-slate-800">
            {entities.length ? entities.map((entity, index) => (
              <tr key={`${entity.type || 'entity'}-${index}`} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${colorMap[entity.type] || 'border-slate-200 bg-slate-100 text-slate-700'}`}>
                    {entity.type || 'UNKNOWN'}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-xs font-medium text-slate-700">
                  {Number.isInteger(entity.start) && Number.isInteger(entity.end)
                    ? `${entity.start}–${entity.end}`
                    : 'Not provided'}
                </td>
                <td className="px-4 py-3 text-xs text-slate-600">
                  <span className="font-medium text-slate-700">{entity.source || 'Unknown'}</span>
                  {Number.isFinite(entity.score) ? ` · ${(entity.score * 100).toFixed(0)}%` : ''}
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-slate-400">No detections available yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
