import { Globe, Languages } from 'lucide-react'

export default function LanguagePanel({ languageProfile, detectedLanguages = [], isMixed = false }) {
  const profile = languageProfile
  const languages = profile?.detected_languages || detectedLanguages
  const scripts = profile?.scripts || {}

  const scriptColors = {
    Latin: 'bg-blue-600',
    Devanagari: 'bg-amber-600',
    Kannada: 'bg-emerald-600',
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2">
          <Languages className="h-5 w-5 text-indigo-600" />
          <h3 className="font-semibold text-slate-900">Language and script</h3>
        </div>
        <div className="flex items-center gap-2">
          {profile?.is_mixed ?? isMixed ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-200 bg-purple-50 px-3 py-1 text-xs font-semibold text-purple-700">
              Code-Mixed Document
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
              <Globe className="h-3 w-3" />
              Single Script
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Detected Languages</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {languages.map((lang) => (
              <span
                key={lang}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-sm font-medium text-slate-800 shadow-sm"
              >
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                {lang}
              </span>
            ))}
          </div>
          {profile?.notes && (
            <p className="mt-2 text-xs italic text-slate-500">{profile.notes}</p>
          )}
          {languages.length === 0 && (
            <p className="mt-2 text-sm text-slate-500">Language details are not available.</p>
          )}
        </div>

        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Script Composition</p>
          <div className="mt-2 space-y-2">
            {Object.entries(scripts).map(([script, ratio]) => (
              <div key={script} className="space-y-1">
                <div className="flex justify-between text-xs text-slate-700">
                  <span className="font-medium">{script} Script</span>
                  <span className="font-mono font-semibold">{Math.round(ratio * 100)}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 border border-slate-200">
                  <div
                    className={`h-full ${scriptColors[script] || 'bg-slate-500'}`}
                    style={{ width: `${Math.round(ratio * 100)}%` }}
                  />
                </div>
              </div>
            ))}
            {Object.keys(scripts).length === 0 && (
              <p className="text-sm text-slate-500">Script details are not available.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
