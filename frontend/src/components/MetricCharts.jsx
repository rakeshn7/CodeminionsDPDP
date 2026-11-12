import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function MetricCharts({ requestTrend = [], piiByCategory = [], entityMetrics = [] }) {
  const defaultColors = ['#38bdf8', '#8b5cf6', '#34d399', '#fbbf24', '#f87171', '#22d3ee', '#ec4899']

  const tooltipStyle = {
    backgroundColor: '#0f172a',
    borderColor: '#334155',
    borderRadius: '0.75rem',
    color: '#f8fafc',
    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
  }

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      {/* Chart 1: Request Volume Trend */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
        <h3 className="mb-4 text-lg font-semibold text-white">Requests Processed Over Time</h3>
        {requestTrend.length ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={requestTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="day" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="requests" name="Total Requests" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="flex h-72 items-center justify-center text-sm text-slate-400">
            No measured request trend is available.
          </p>
        )}
      </div>

      {/* Chart 2: PII Entities by Category */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
        <h3 className="mb-4 text-lg font-semibold text-white">PII Entities by Category</h3>
        {piiByCategory.length ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={piiByCategory}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={3}
                >
                  {piiByCategory.map((entry, index) => (
                    <Cell key={entry.name} fill={defaultColors[index % defaultColors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ color: '#cbd5e1' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="flex h-72 items-center justify-center text-sm text-slate-400">
            No measured entity totals are available.
          </p>
        )}
      </div>

      {/* Chart 3: Detection Precision vs Recall */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel xl:col-span-2">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Detection Precision vs Recall by Entity Type</h3>
          <span className="text-xs text-slate-400">Target Benchmark: 1.00 (100%)</span>
        </div>
        {entityMetrics.length ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={entityMetrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis domain={[0, 1]} stroke="#94a3b8" tickFormatter={(v) => `${Math.round(v * 100)}%`} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value) => [`${(Number(value) * 100).toFixed(1)}%`]}
                />
                <Legend wrapperStyle={{ color: '#cbd5e1' }} />
                <Bar dataKey="precision" name="Precision" fill="#10b981" radius={[6, 6, 0, 0]} />
                <Bar dataKey="recall" name="Recall" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="flex h-72 items-center justify-center text-sm text-slate-400">
            Detection precision and recall are not available until a labeled dataset is evaluated.
          </p>
        )}
      </div>
    </div>
  )
}
