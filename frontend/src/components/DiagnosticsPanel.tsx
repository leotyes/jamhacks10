import { Activity, AlertTriangle, ShieldCheck } from 'lucide-react';

interface DiagnosticsPanelProps {
  confidence: number;
  log: string;
}

export function DiagnosticsPanel({ confidence, log }: DiagnosticsPanelProps) {
  const percentage = Math.round(confidence * 100);
  
  let colorClass = 'text-emerald-400';
  let bgClass = 'bg-emerald-500/10 border-emerald-500/20';
  let Icon = ShieldCheck;
  
  if (percentage < 80) {
    colorClass = 'text-amber-400';
    bgClass = 'bg-amber-500/10 border-amber-500/20';
    Icon = AlertTriangle;
  }
  
  if (percentage < 60) {
    colorClass = 'text-red-400';
    bgClass = 'bg-red-500/10 border-red-500/20';
    Icon = Activity;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-xl font-semibold text-slate-100">Step 2: AI Diagnostics</h2>
        <p className="text-sm text-slate-400">Review confidence scores and detailed analysis logs.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Confidence Score Card */}
        <div className={`p-6 rounded-xl border flex flex-col items-center justify-center space-y-4 ${bgClass}`}>
          <div className="flex items-center space-x-2">
            <Icon className={`w-5 h-5 ${colorClass}`} />
            <span className="text-sm font-medium text-slate-300">Confidence Score</span>
          </div>
          
          <div className="relative flex items-center justify-center">
            {/* Simple CSS radial progress indicator */}
            <svg className="w-32 h-32 transform -rotate-90">
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="currentColor"
                strokeWidth="8"
                fill="transparent"
                className="text-slate-800"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="currentColor"
                strokeWidth="8"
                fill="transparent"
                strokeDasharray="351.858"
                strokeDashoffset={351.858 - (351.858 * percentage) / 100}
                className={`${colorClass} transition-all duration-1000 ease-out`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center flex-col">
              <span className={`text-3xl font-bold ${colorClass}`}>{percentage}%</span>
            </div>
          </div>
        </div>

        {/* AI Reasoning Log */}
        <div className="lg:col-span-2 bg-slate-950 border border-slate-800 rounded-xl flex flex-col overflow-hidden relative group">
          <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></div>
            </div>
            <span className="text-xs text-slate-500 font-mono">system.log</span>
          </div>
          <div className="p-4 overflow-y-auto max-h-[160px] font-mono text-sm leading-relaxed text-slate-300">
            {log.split('\n').map((line, i) => (
              <div key={i} className="mb-1">
                <span className="text-slate-600 mr-3 select-none">{String(i + 1).padStart(2, '0')}</span>
                {line}
              </div>
            ))}
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-slate-950 to-transparent pointer-events-none"></div>
        </div>
      </div>
    </div>
  );
}
