import { useState } from 'react';
import { Code2, Cpu, Network } from 'lucide-react';

interface OutputTabsProps {
  netlist: any;
  schematicUrl?: string;
}

export function OutputTabs({ netlist }: OutputTabsProps) {
  const [activeTab, setActiveTab] = useState<'netlist' | 'schematic' | 'graph'>('netlist');


  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl shadow-black/50">
      <div className="flex border-b border-slate-800 bg-slate-950/50">
        <button
          onClick={() => setActiveTab('netlist')}
          className={`flex-1 py-3 px-4 flex items-center justify-center space-x-2 text-sm font-medium transition-colors ${
            activeTab === 'netlist'
              ? 'text-indigo-400 border-b-2 border-indigo-500 bg-indigo-500/5'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Code2 className="w-4 h-4" />
          <span>Validated Netlist</span>
        </button>
        <button
          onClick={() => setActiveTab('schematic')}
          className={`flex-1 py-3 px-4 flex items-center justify-center space-x-2 text-sm font-medium transition-colors ${
            activeTab === 'schematic'
              ? 'text-emerald-400 border-b-2 border-emerald-500 bg-emerald-500/5'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>Schematic Viewer</span>
        </button>
        <button
          onClick={() => setActiveTab('graph')}
          className={`flex-1 py-3 px-4 flex items-center justify-center space-x-2 text-sm font-medium transition-colors ${
            activeTab === 'graph'
              ? 'text-cyan-400 border-b-2 border-cyan-500 bg-cyan-500/5'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Network className="w-4 h-4" />
          <span>Graph Explorer</span>
        </button>
      </div>

      <div className="flex-1 p-0 overflow-hidden relative bg-slate-950/50 min-h-[400px]">
        {activeTab === 'netlist' && (
          <div className="absolute inset-0 p-4 overflow-auto">
            <pre className="text-sm font-mono text-slate-300">
              <code>{JSON.stringify(netlist, null, 2)}</code>
            </pre>
          </div>
        )}

        {activeTab === 'schematic' && (
          <div className="absolute inset-0 flex items-center justify-center flex-col p-8">
            <div className="w-full max-w-lg aspect-video rounded-lg border border-slate-700 bg-slate-800/50 flex flex-col items-center justify-center relative overflow-hidden group">
              {/* Mock Schematic Graphic */}
              <svg viewBox="0 0 100 100" className="w-full h-full opacity-30 text-emerald-500" fill="none" stroke="currentColor" strokeWidth="1">
                <path d="M10,50 L30,50 M30,40 L30,60 L50,60 L50,40 Z M50,50 L70,50 M70,45 L70,55 M75,45 L75,55 M75,50 L90,50" />
                <circle cx="20" cy="50" r="2" fill="currentColor" />
                <circle cx="80" cy="50" r="2" fill="currentColor" />
              </svg>
              <div className="absolute inset-0 bg-slate-900/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-sm">
                <button className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium shadow-lg transition-transform transform hover:scale-105">
                  Download .kicad_sch
                </button>
              </div>
            </div>
            <p className="mt-6 text-slate-400 text-sm text-center max-w-md">
              A generated KiCad schematic based on the reconciled layout. Hover to download the source file.
            </p>
          </div>
        )}

        {activeTab === 'graph' && (
          <div className="absolute inset-0 flex items-center justify-center flex-col">
            <Network className="w-16 h-16 text-cyan-500/20 mb-4" />
            <h3 className="text-lg font-medium text-slate-200">NetworkX Graph Visualization</h3>
            <p className="text-slate-500 mt-2 text-sm">Interactive node graph explorer placeholder.</p>
          </div>
        )}
      </div>
    </div>
  );
}
