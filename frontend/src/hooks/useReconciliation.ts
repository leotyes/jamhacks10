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
<<<<<<< HEAD
  const [sideImageFile, setSideImageFile] = useState<File | null>(null);
  const [topImageFile, setTopImageFile] = useState<File | null>(null);
=======
  const [topImage, setTopImage] = useState<File | null>(null);   // Top-down breadboard photo
  const [sideImage, setSideImage] = useState<File | null>(null); // Side/profile breadboard photo
>>>>>>> db435c23da0177b53cd0f11446a1d181ce0bab67
  const [parts, setParts] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [result, setResult] = useState<ReconciliationResult | null>(null);

  const canRun = !!(iocFile && topImage && sideImage);

  const runReconciliation = async () => {
<<<<<<< HEAD
    if (!iocFile || !sideImageFile || !topImageFile) return;
=======
    if (!iocFile || !topImage || !sideImage) return;
>>>>>>> db435c23da0177b53cd0f11446a1d181ce0bab67

    setIsProcessing(true);
    setStatusText('Parsing .ioc layout...');

<<<<<<< HEAD
    setTimeout(() => setStatusText('Analyzing breadboard images...'), 1000);
    setTimeout(() => setStatusText('Integrating component manifest...'), 1800);
    setTimeout(() => setStatusText('Reconciling graphs...'), 2400);
=======
    setTimeout(() => setStatusText('Analyzing top-view image...'), 1000);
    setTimeout(() => setStatusText('Analyzing side-view image...'), 1800);
    setTimeout(() => setStatusText('Integrating component manifest...'), 2600);
    setTimeout(() => setStatusText('Reconciling graphs...'), 3400);
>>>>>>> db435c23da0177b53cd0f11446a1d181ce0bab67

    try {
      const formData = new FormData();
      formData.append('ioc_file', iocFile);
<<<<<<< HEAD
      formData.append('side_image', sideImageFile);
      formData.append('top_image', topImageFile);
=======
      formData.append('top_image', topImage);
      formData.append('side_image', sideImage);
>>>>>>> db435c23da0177b53cd0f11446a1d181ce0bab67
      formData.append('parts', JSON.stringify(parts));

      const response = await axios.post('http://127.0.0.1:8000/api/reconcile', formData);

      setResult({
        confidence: response.data.confidence,
        log: response.data.reasoning_log,
        netlist: response.data.netlist,
        schematicUrl: response.data.schematic_url,
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
<<<<<<< HEAD
    sideImageFile, setSideImageFile,
    topImageFile, setTopImageFile,
    parts, setParts,
    isProcessing, statusText,
=======
    topImage, setTopImage,
    sideImage, setSideImage,
    parts, setParts,
    isProcessing, statusText, canRun,
>>>>>>> db435c23da0177b53cd0f11446a1d181ce0bab67
    result, runReconciliation,
    reset: () => {
      setResult(null);
      setIocFile(null);
<<<<<<< HEAD
      setSideImageFile(null);
      setTopImageFile(null);
      setParts([]);
    },
=======
      setTopImage(null);
      setSideImage(null);
      setParts([]);
    }
>>>>>>> db435c23da0177b53cd0f11446a1d181ce0bab67
  };
}
