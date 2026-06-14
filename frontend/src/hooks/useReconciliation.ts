import { useState } from 'react';
import axios from 'axios';

export interface ReconciliationResult {
  confidence: number;
  log: string;
  netlist: any;
  schematicUrl: string;
  geometryUrl: string;
}

export function useReconciliation() {
  const [iocFile, setIocFile] = useState<File | null>(null);
  const [sideImageFile, setSideImageFile] = useState<File | null>(null);
  const [topImageFile, setTopImageFile] = useState<File | null>(null);
  const [parts, setParts] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [result, setResult] = useState<ReconciliationResult | null>(null);

  const runReconciliation = async () => {
    if (!iocFile || !sideImageFile || !topImageFile) return;

    setIsProcessing(true);
    await new Promise(resolve => setTimeout(resolve, 10000));
    setStatusText('Parsing .ioc layout...');

    setTimeout(() => setStatusText('Analyzing breadboard images...'), 1000);
    setTimeout(() => setStatusText('Integrating component manifest...'), 1800);
    setTimeout(() => setStatusText('Reconciling graphs...'), 2400);

    try {
      const formData = new FormData();
      formData.append('ioc_file', iocFile);
      formData.append('side_image', sideImageFile);
      formData.append('top_image', topImageFile);
      formData.append('parts', JSON.stringify(parts));

      const response = await axios.post('http://127.0.0.1:8000/api/reconcile', formData);

      setResult({
        confidence: response.data.confidence,
        log: response.data.reasoning_log,
        netlist: response.data.netlist,
        schematicUrl: response.data.schematic_url,
        geometryUrl: response.data.geometry_url,
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
    iocFile, setIocFile,
    sideImageFile, setSideImageFile,
    topImageFile, setTopImageFile,
    parts, setParts,
    isProcessing, statusText,
    result, runReconciliation,
    reset: () => {
      setResult(null);
      setIocFile(null);
      setSideImageFile(null);
      setTopImageFile(null);
      setParts([]);
    },
  };
}
