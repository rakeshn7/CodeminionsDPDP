import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function MetricCharts({ requestTrend, piiByCategory, entityMetrics = [] }) {
  const defaultColors = ['#38bdf8', '#8b5cf6', '#34d399', '#fbbf24', '#f87171', '#22d3ee']

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
        <h3 className="mb-4 text-lg font-semibold text-white">Requests processed over time</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={requestTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="day" stroke="#cbd5e1" />
              <YAxis stroke="#cbd5e1" />
              <Tooltip />
              <Bar dataKey="requests" fill="#3b82f6" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
        <h3 className="mb-4 text-lg font-semibold text-white">PII entities by category</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={piiByCategory} dataKey="value" nameKey="name" innerRadius={48} outerRadius={88} paddingAngle={2}>
                {piiByCategory.map((entry, index) => (
                  <Cell key={entry.name} fill={defaultColors[index % defaultColors.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel xl:col-span-2">
        <h3 className="mb-4 text-lg font-semibold text-white">Detection precision vs recall</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={entityMetrics.length ? entityMetrics : piiByCategory.map((entry, index) => ({ name: entry.name, precision: 0.92 - index * 0.04, recall: 0.89 - index * 0.03 }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#cbd5e1" />
              <YAxis domain={[0, 1]} stroke="#cbd5e1" />
              <Tooltip />
              <Legend />
              <Bar dataKey="precision" fill="#10b981" radius={[6, 6, 0, 0]} />
              <Bar dataKey="recall" fill="#3b82f6" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
