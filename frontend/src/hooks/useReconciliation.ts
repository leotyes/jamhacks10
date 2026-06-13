import { useState } from 'react';
// import axios from 'axios';

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
      /*
      // EXPLICIT AXIOS CALL FOR FUTURE BACKEND SWAP
      const formData = new FormData();
      formData.append('ioc', iocFile);
      formData.append('image', imageFile);
      formData.append('parts', JSON.stringify(parts));
      const response = await axios.post('/api/reconcile', formData);
      setResult(response.data);
      */

      // MOCK BACKEND DELAY & RESPONSE
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      const componentMatches = parts.length > 0 
        ? parts.map((part) => `Verified user-specified part: "${part}"`).join('\n')
        : "No custom component manifest provided. Relying on visual parsing.";


      setResult({
        confidence: parts.length > 0 ? 0.98 : 0.94, // Custom parts boost confidence!
        log: `✅ Analysis Complete\n------------------\n${componentMatches}\n\nDetected 1x Red LED, 1x 220Ω Resistor...\nMatched row 15 to STM32 Pin PA5...\nNo short circuits detected.\nNetlist graphs match with ${parts.length > 0 ? '98%' : '94%'} structural similarity.`,
        netlist: {
          "components": [
            { "id": "U1", "type": "STM32F401" },
            { "id": "D1", "type": "LED", "color": "Red" },
            { "id": "R1", "type": "Resistor", "value": "220Ω" },
            ...parts.map((part, i) => ({ "id": `X${i+1}`, "type": part }))
          ],
          "nets": [
            { "id": "N1", "nodes": ["U1.PA5", "D1.A"] },
            { "id": "N2", "nodes": ["D1.K", "R1.1"] },
            { "id": "GND", "nodes": ["R1.2", "U1.GND"] }
          ]
        },
        schematicUrl: "mock_schematic"
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

