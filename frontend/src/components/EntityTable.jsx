export default function EntityTable({ entities = [] }) {
  const colorMap = {
    PERSON: 'bg-sky-500/10 text-sky-200 border-sky-500/30',
    AADHAAR: 'bg-violet-500/10 text-violet-200 border-violet-500/30',
    PAN: 'bg-cyan-500/10 text-cyan-200 border-cyan-500/30',
    ADDRESS: 'bg-amber-500/10 text-amber-200 border-amber-500/30',
    GSTIN: 'bg-rose-500/10 text-rose-200 border-rose-500/30',
    VOTER_ID: 'bg-emerald-500/10 text-emerald-200 border-emerald-500/30',
    PASSPORT: 'bg-pink-500/10 text-pink-200 border-pink-500/30',
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Detected Entity Map</h3>
        <span className="rounded-full border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-300">{entities.length} entries</span>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-700">
        <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
          <thead className="bg-slate-950 text-slate-300">
            <tr>
              <th className="px-4 py-3 font-medium">Entity type</th>
              <th className="px-4 py-3 font-medium">Placeholder</th>
              <th className="px-4 py-3 font-medium">Detection status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-900 text-slate-200">
            {entities.length ? entities.map((entity, index) => (
              <tr key={`${entity.type || 'entity'}-${index}`}>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full border px-2 py-1 text-xs font-medium ${colorMap[entity.type] || 'border-slate-600 bg-slate-800 text-slate-200'}`}>
                    {entity.type || 'UNKNOWN'}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-200">{entity.placeholder || `${(entity.type || 'ENTITY').toUpperCase()}_${index + 1}`}</td>
                <td className="px-4 py-3">
                  <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-200">
                    {entity.status || 'Detected'}
                  </span>
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
