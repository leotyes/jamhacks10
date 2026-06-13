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
  const [topImage, setTopImage] = useState<File | null>(null);   // Top-down breadboard photo
  const [sideImage, setSideImage] = useState<File | null>(null); // Side/profile breadboard photo
  const [parts, setParts] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [result, setResult] = useState<ReconciliationResult | null>(null);

  const canRun = !!(iocFile && topImage && sideImage);

  const runReconciliation = async () => {
    if (!iocFile || !topImage || !sideImage) return;

    setIsProcessing(true);
    setStatusText('Parsing .ioc layout...');

    setTimeout(() => setStatusText('Analyzing top-view image...'), 1000);
    setTimeout(() => setStatusText('Analyzing side-view image...'), 1800);
    setTimeout(() => setStatusText('Integrating component manifest...'), 2600);
    setTimeout(() => setStatusText('Reconciling graphs...'), 3400);

    try {
      const formData = new FormData();
      formData.append('ioc_file', iocFile);
      formData.append('top_image', topImage);
      formData.append('side_image', sideImage);
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
    iocFile, setIocFile,
    topImage, setTopImage,
    sideImage, setSideImage,
    parts, setParts,
    isProcessing, statusText, canRun,
    result, runReconciliation,
    reset: () => {
      setResult(null);
      setIocFile(null);
      setTopImage(null);
      setSideImage(null);
      setParts([]);
    }
  };
}
