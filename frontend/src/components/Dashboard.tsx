import { Cpu, RefreshCcw } from 'lucide-react';
import { useReconciliation } from '../hooks/useReconciliation';
import { UploadPanel } from './UploadPanel';
import { DiagnosticsPanel } from './DiagnosticsPanel';
import { OutputTabs } from './OutputTabs';

export function Dashboard() {
  const {
    iocFile, setIocFile,
    imageFile, setImageFile,
    parts, setParts,
    isProcessing, statusText,
    result, runReconciliation, reset
  } = useReconciliation();


  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col font-sans">
      {/* Top Navigation */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/80 px-6 flex items-center justify-between sticky top-0 z-10 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-emerald-400">
            Hardware Recon AI
          </h1>
        </div>
        
        {result && (
          <button 
            onClick={reset}
            className="flex items-center space-x-2 text-sm text-slate-400 hover:text-slate-200 transition-colors px-3 py-1.5 rounded-md hover:bg-slate-800"
          >
            <RefreshCcw className="w-4 h-4" />
            <span>New Session</span>
          </button>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Column: Upload & Controls */}
          <div className="lg:col-span-5 space-y-8">
            <UploadPanel 
              iocFile={iocFile} setIocFile={setIocFile}
              imageFile={imageFile} setImageFile={setImageFile}
              parts={parts} setParts={setParts}
              onRun={runReconciliation}
              isProcessing={isProcessing}
              statusText={statusText}
            />


            {/* Step indicator helper text */}
            {!result && !isProcessing && (
              <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/20 text-indigo-200 text-sm">
                <p><strong>Note:</strong> Upload both files to proceed. We will extract netlists from your .ioc file and use Vision AI on the photo to reconcile any discrepancies.</p>
              </div>
            )}
          </div>

          {/* Right Column: Results & Diagnostics */}
          <div className="lg:col-span-7 space-y-8 flex flex-col">
            {result ? (
              <>
                <DiagnosticsPanel 
                  confidence={result.confidence} 
                  log={result.log} 
                />
                <div className="flex-1 min-h-[400px]">
                  <OutputTabs 
                    netlist={result.netlist} 
                    schematicUrl={result.schematicUrl} 
                  />
                </div>
              </>
            ) : (
              <div className="flex-1 min-h-[500px] border border-dashed border-slate-800 rounded-xl flex items-center justify-center bg-slate-900/20">
                <div className="text-center space-y-4 opacity-50">
                  <div className="w-16 h-16 mx-auto rounded-full bg-slate-800 flex items-center justify-center mb-4">
                    <Cpu className="w-8 h-8 text-slate-500" />
                  </div>
                  <h3 className="text-lg font-medium text-slate-400">Awaiting Data</h3>
                  <p className="text-sm text-slate-500 max-w-xs mx-auto">Run the AI reconciliation to view diagnostics, validated netlists, and generated schematics here.</p>
                </div>
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}
