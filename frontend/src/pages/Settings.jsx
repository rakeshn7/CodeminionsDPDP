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
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Privacy Policies</p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">Policy configuration preview</h2>
      </div>

      <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4 text-sm text-emerald-900 shadow-xs">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 shrink-0" />
          <span>
            This configuration is visible in the frontend only until the backend confirms policy enforcement.
          </span>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-bold text-slate-900">Purpose selection</h3>
          <div className="mt-4 space-y-3">
            {purposeOptions.map((purpose) => (
              <button
                key={purpose}
                type="button"
                onClick={() => setPolicy((current) => ({ ...current, purpose }))}
                className={[
                  'flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm transition',
                  policy.purpose === purpose
                    ? 'border-blue-300 bg-blue-50 text-blue-900 font-semibold ring-1 ring-blue-200 shadow-xs'
                    : 'border-slate-200 bg-slate-50/50 text-slate-700 hover:bg-slate-100/80',
                ].join(' ')}
              >
                <span>{purpose}</span>
                {policy.purpose === purpose && <CheckCircle2 className="h-4 w-4 text-blue-600" />}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900">PII action matrix</h3>
            <div className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.15em] text-slate-600">
              <Lock className="h-3.5 w-3.5" />
              {policy.active ? 'Active' : 'Frontend preview only'}
            </div>
          </div>

          <div className="space-y-3">
            {piiCategories.map((category) => (
              <div key={category} className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 md:grid-cols-[0.8fr_1.2fr] md:items-center">
                <div className="text-sm font-semibold text-slate-900">{category}</div>
                <div className="flex flex-wrap gap-2">
                  {actionOptions.map((action) => (
                    <button
                      key={action}
                      type="button"
                      onClick={() => updateRule(category, action)}
                      className={[
                        'rounded-lg border px-3 py-1.5 text-xs font-semibold transition',
                        policy.rules[category] === action
                          ? 'border-emerald-300 bg-emerald-50 text-emerald-800 shadow-xs'
                          : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900',
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

      <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 text-sm text-amber-900 shadow-xs">
        <p className="mb-2 flex items-center gap-2 font-semibold text-amber-900">
          <ShieldAlert className="h-4 w-4 text-amber-600" />
          Enforcement note
        </p>
        <p className="text-sm text-amber-800">
          These controls only update local page state. The backend does not currently receive or enforce these policy settings.
        </p>
      </div>
    </div>
  )
}
