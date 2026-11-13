import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function MetricCharts({ requestTrend = [], piiByCategory = [], entityMetrics = [] }) {
  const defaultColors = ['#0284c7', '#7c3aed', '#059669', '#d97706', '#e11d48', '#0891b2', '#db2777']

  const tooltipStyle = {
    backgroundColor: '#ffffff',
    borderColor: '#e2e8f0',
    borderRadius: '0.75rem',
    color: '#0f172a',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  }

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      {/* Chart 1: Request Volume Trend */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-slate-900">Requests Processed Over Time</h3>
        {requestTrend.length ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={requestTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="day" stroke="#64748b" tick={{ fontSize: 12 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="requests" name="Total Requests" fill="#2563eb" radius={[6, 6, 0, 0]} />
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
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-slate-900">PII Entities by Category</h3>
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
                <Legend wrapperStyle={{ color: '#475569', fontSize: 12 }} />
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
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm xl:col-span-2">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-base font-semibold text-slate-900">Detection Precision vs Recall by Entity Type</h3>
        </div>
        {entityMetrics.length ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={entityMetrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 1]} stroke="#64748b" tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value) => [`${(Number(value) * 100).toFixed(1)}%`]}
                />
                <Legend wrapperStyle={{ color: '#475569', fontSize: 12 }} />
                <Bar dataKey="precision" name="Precision" fill="#059669" radius={[6, 6, 0, 0]} />
                <Bar dataKey="recall" name="Recall" fill="#2563eb" radius={[6, 6, 0, 0]} />
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
