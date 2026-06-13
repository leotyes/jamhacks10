import { useState } from 'react';
import axios from 'axios';

export interface ReconciliationResult {
  confidence: number;
  log: string;
  netlist: any;
  schematicUrl: string;
}

export function useReconciliation() {
  const [iocFile, setIocFile] = useState<File | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [parts, setParts] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [result, setResult] = useState<ReconciliationResult | null>(null);

  const runReconciliation = async () => {
    if (!iocFile || !imageFile) return;

    setIsProcessing(true);
    setStatusText('Parsing .ioc layout...');
    
    // Simulate a multi-step backend process
    setTimeout(() => setStatusText('Analyzing breadboard image...'), 1000);
    setTimeout(() => setStatusText('Integrating component manifest...'), 1800);
    setTimeout(() => setStatusText('Reconciling graphs...'), 2400);

    try {
      // EXPLICIT AXIOS CALL FOR FUTURE BACKEND SWAP
      const formData = new FormData();
      formData.append('ioc_file', iocFile);
      formData.append('image_file', imageFile);
      formData.append('parts', JSON.stringify(parts));
      const response = await axios.post('http://127.0.0.1:8000/api/reconcile', formData);
      
      setResult({
        confidence: response.data.confidence,
        log: response.data.reasoning_log,
        netlist: response.data.netlist,
        schematicUrl: response.data.schematic_url
      });
    } catch (error) {
      console.error(error);
      setStatusText('Error during reconciliation');
    } finally {
      setIsProcessing(false);
      setStatusText('');
    }
  };

  return {
    iocFile,
    setIocFile,
    imageFile,
    setImageFile,
    parts,
    setParts,
    isProcessing,
    statusText,
    result,
    runReconciliation,
    reset: () => { setResult(null); setIocFile(null); setImageFile(null); setParts([]); }
  };
}

