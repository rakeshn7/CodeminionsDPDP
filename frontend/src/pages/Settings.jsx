import { CheckCircle2, Lock, ShieldAlert } from 'lucide-react'
import { useState } from 'react'
import { defaultPolicy } from '../data/samples'

const purposeOptions = ['Loan processing', 'Marketing', 'KYC verification', 'Customer support', 'Insurance claims']
const piiCategories = ['PERSON', 'AADHAAR', 'PAN', 'GSTIN', 'VOTER_ID', 'PASSPORT', 'ADDRESS']
const actionOptions = ['Mask', 'Block', 'Allow']

export default function Settings() {
  const [policy, setPolicy] = useState(defaultPolicy)

  const updateRule = (category, value) => {
    setPolicy((current) => ({
      ...current,
      rules: {
        ...current.rules,
        [category]: value,
      },
    }))
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Privacy Policies</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">Policy configuration and enforcement status</h2>
      </div>

      <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-300" />
          <span>
            This configuration is visible in the frontend only until the backend confirms policy enforcement.
          </span>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <h3 className="text-lg font-semibold text-white">Purpose selection</h3>
          <div className="mt-4 space-y-3">
            {purposeOptions.map((purpose) => (
              <button
                key={purpose}
                type="button"
                onClick={() => setPolicy((current) => ({ ...current, purpose }))}
                className={[
                  'flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm transition',
                  policy.purpose === purpose
                    ? 'border-blue-500/40 bg-blue-500/10 text-blue-100'
                    : 'border-slate-700 bg-slate-950 text-slate-200 hover:border-slate-600',
                ].join(' ')}
              >
                <span>{purpose}</span>
                {policy.purpose === purpose && <CheckCircle2 className="h-4 w-4 text-blue-300" />}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">PII action matrix</h3>
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-slate-300">
              <Lock className="h-3.5 w-3.5" />
              {policy.active ? 'Active' : 'Configured in frontend'}
            </div>
          </div>

          <div className="space-y-3">
            {piiCategories.map((category) => (
              <div key={category} className="grid gap-3 rounded-xl border border-slate-700 bg-slate-950 p-3 md:grid-cols-[0.8fr_1.2fr] md:items-center">
                <div className="text-sm font-medium text-white">{category}</div>
                <div className="flex flex-wrap gap-2">
                  {actionOptions.map((action) => (
                    <button
                      key={action}
                      type="button"
                      onClick={() => updateRule(category, action)}
                      className={[
                        'rounded-lg border px-3 py-1.5 text-xs font-medium transition',
                        policy.rules[category] === action
                          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100'
                          : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500',
                      ].join(' ')}
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
        <p className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-200">
          <ShieldAlert className="h-4 w-4 text-amber-300" />
          Enforcement note
        </p>
        <p className="text-sm text-slate-300">
          Policy settings are ready to be wired to backend enforcement once the backend service exposes policy state. Until then, the interface demonstrates intended behavior without claiming enforcement.
        </p>
      </div>
    </div>
  )
}
