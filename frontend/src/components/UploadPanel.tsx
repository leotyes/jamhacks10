import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileCode, Image as ImageIcon, CheckCircle2, UploadCloud, Loader2, Plus, X, Package } from 'lucide-react';

interface UploadPanelProps {
  iocFile: File | null;
  setIocFile: (file: File | null) => void;
  imageFile: File | null;
  setImageFile: (file: File | null) => void;
  parts: string[];
  setParts: React.Dispatch<React.SetStateAction<string[]>>;
  onRun: () => void;
  isProcessing: boolean;
  statusText: string;
}

export function UploadPanel({
  iocFile,
  setIocFile,
  imageFile,
  setImageFile,
  parts,
  setParts,
  onRun,
  isProcessing,
  statusText
}: UploadPanelProps) {
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [newPart, setNewPart] = useState('');

  const onDropIoc = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setIocFile(acceptedFiles[0]);
    }
  }, [setIocFile]);

  const onDropImage = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setImageFile(file);
      const objectUrl = URL.createObjectURL(file);
      setImagePreview(objectUrl);
    }
  }, [setImageFile]);

  const { getRootProps: getIocRootProps, getInputProps: getIocInputProps, isDragActive: isIocDragActive } = useDropzone({
    onDrop: onDropIoc,
    accept: { 'application/octet-stream': ['.ioc'] },
    maxFiles: 1
  });

  const { getRootProps: getImageRootProps, getInputProps: getImageInputProps, isDragActive: isImageDragActive } = useDropzone({
    onDrop: onDropImage,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png'] },
    maxFiles: 1
  });

  const handleAddPart = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPart.trim()) {
      setParts(prev => [...prev, newPart.trim()]);
      setNewPart('');
    }
  };

  const handleRemovePart = (indexToRemove: number) => {
    setParts(prev => prev.filter((_, idx) => idx !== indexToRemove));
  };

  const formatFileSize = (bytes: number) => {
    return (bytes / 1024).toFixed(2) + ' KB';
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-xl font-semibold text-slate-100">Step 1: Upload Layout, Image & Parts</h2>
        <p className="text-sm text-slate-400">Provide configuration, a breadboard photo, and any specific component identifiers.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Zone A: IOC File */}
        <div
          {...getIocRootProps()}
          className={`relative overflow-hidden flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl transition-all cursor-pointer ${
            isIocDragActive ? 'border-indigo-500 bg-indigo-500/10' : iocFile ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-slate-700 hover:border-slate-500 bg-slate-900/50'
          }`}
        >
          <input {...getIocInputProps()} />
          {iocFile ? (
            <div className="flex flex-col items-center text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-emerald-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-200">{iocFile.name}</p>
                <p className="text-xs text-slate-400">{formatFileSize(iocFile.size)}</p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mb-2">
                <FileCode className="w-6 h-6 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-300">Drag & drop your .ioc file</p>
              <p className="text-xs text-slate-500">or click to browse</p>
            </div>
          )}
        </div>

        {/* Zone B: Image File */}
        <div
          {...getImageRootProps()}
          className={`relative overflow-hidden flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl transition-all cursor-pointer min-h-[160px] ${
            isImageDragActive ? 'border-indigo-500 bg-indigo-500/10' : imageFile ? 'border-emerald-500/50' : 'border-slate-700 hover:border-slate-500 bg-slate-900/50'
          }`}
        >
          <input {...getImageInputProps()} />
          {imagePreview ? (
            <div className="absolute inset-0 w-full h-full">
              <img src={imagePreview} alt="Preview" className="w-full h-full object-cover opacity-60" />
              <div className="absolute inset-0 bg-slate-950/40 flex items-center justify-center flex-col backdrop-blur-[2px]">
                <div className="w-12 h-12 rounded-full bg-emerald-500/30 flex items-center justify-center shadow-lg border border-emerald-500/50 mb-2">
                  <CheckCircle2 className="w-6 h-6 text-emerald-300" />
                </div>
                <p className="text-sm font-medium text-white shadow-sm drop-shadow-md">{imageFile?.name}</p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mb-2">
                <ImageIcon className="w-6 h-6 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-300">Upload breadboard photo</p>
              <p className="text-xs text-slate-500">JPEG, JPG, or PNG</p>
            </div>
          )}
        </div>
      </div>

      {/* Input Section C: Specific Parts (New) */}
      <div className="border border-slate-800 bg-slate-900/50 rounded-xl p-5 flex flex-col gap-4">
        <div className="flex items-center space-x-2">
          <Package className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-200">Specific Component Manifest (BOM)</h3>
        </div>
        
        <form onSubmit={handleAddPart} className="flex gap-2">
          <input
            type="text"
            value={newPart}
            onChange={(e) => setNewPart(e.target.value)}
            placeholder="Add part e.g., 555 Timer, L7805, 10uF Capacitor"
            className="flex-1 bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-slate-200 outline-none transition-colors"
          />
          <button
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-500 border border-indigo-500 text-white rounded-lg p-2 transition-colors flex items-center justify-center"
          >
            <Plus className="w-5 h-5" />
          </button>
        </form>

        <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto pr-1">
          {parts.length === 0 ? (
            <span className="text-xs text-slate-500 italic">No parts added yet. Add specific ICs or modules to enhance AI matching.</span>
          ) : (
            parts.map((part, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-500/10 border border-indigo-500/30 text-indigo-300"
              >
                {part}
                <button
                  type="button"
                  onClick={() => handleRemovePart(index)}
                  className="text-indigo-400 hover:text-indigo-200 focus:outline-none"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))
          )}
        </div>
      </div>

      <div className="mt-2">
        <button
          onClick={onRun}
          disabled={!iocFile || !imageFile || isProcessing}
          className={`w-full py-4 rounded-xl flex items-center justify-center space-x-3 text-lg font-medium transition-all shadow-lg ${
            !iocFile || !imageFile
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
              : isProcessing
              ? 'bg-indigo-600/80 text-white cursor-wait border border-indigo-500/50'
              : 'bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500 hover:shadow-indigo-500/25 hover:scale-[1.01]'
          }`}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>{statusText || 'Processing...'}</span>
            </>
          ) : (
            <>
              <UploadCloud className="w-5 h-5" />
              <span>Run AI Reconciliation</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
