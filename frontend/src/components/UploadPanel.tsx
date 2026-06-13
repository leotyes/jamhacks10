import { Loader2, UploadCloud, FileCode, Image as ImageIcon, CheckCircle2, Plus, X, Package, ArrowUp, ArrowRight } from "lucide-react"
import React, { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { ScrambleTextOnHover } from "./ScrambleText"

interface UploadPanelProps {
  iocFile: File | null
  setIocFile: (file: File | null) => void
  topImage: File | null
  setTopImage: (file: File | null) => void
  sideImage: File | null
  setSideImage: (file: File | null) => void
  parts: string[]
  setParts: React.Dispatch<React.SetStateAction<string[]>>
  onRun: () => void
  isProcessing: boolean
  canRun: boolean
  statusText: string
}

// Shared image dropzone component
function ImageDropZone({
  label,
  hint,
  file,
  onDrop,
  onClear,
  Icon,
}: {
  label: string
  hint: string
  file: File | null
  onDrop: (files: File[]) => void
  onClear: () => void
  Icon: React.ElementType
}) {
  const [preview, setPreview] = useState<string | null>(null)

  const handleDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const f = acceptedFiles[0]
      onDrop([f])
      setPreview(URL.createObjectURL(f))
    }
  }, [onDrop])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleDrop,
    accept: { "image/*": [".jpeg", ".jpg", ".png"] },
    maxFiles: 1
  })

  return (
    <div className={`relative border cursor-pointer transition-all duration-300 group overflow-hidden ${
      isDragActive ? "border-accent bg-accent/5"
      : file ? "border-accent/50 bg-accent/5"
      : "border-border hover:border-accent/40 bg-card"
    }`}>
      <div {...getRootProps()} className="p-5 flex flex-col items-center justify-center gap-3 min-h-[120px]">
        <input {...getInputProps()} />
        {file && preview ? (
          <>
            <img src={preview} alt="Preview" className="absolute inset-0 w-full h-full object-cover opacity-30" />
            <div className="relative z-10 flex flex-col items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-accent" />
              <p className="font-mono text-xs text-foreground text-center leading-tight max-w-[160px] truncate">{file.name}</p>
              <p className="font-mono text-[9px] text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center">
            <div className="w-10 h-10 border border-border flex items-center justify-center group-hover:border-accent/40 transition-colors">
              <Icon className="w-5 h-5 text-muted-foreground" />
            </div>
            <p className="font-mono text-xs text-foreground">{label}</p>
            <p className="font-mono text-[9px] text-muted-foreground">{hint}</p>
          </div>
        )}
      </div>
      {/* Clear button */}
      {file && (
        <button
          onClick={(e) => { e.stopPropagation(); onClear(); setPreview(null) }}
          className="absolute top-2 right-2 z-20 bg-background/80 hover:bg-accent hover:text-accent-foreground border border-border p-1 transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      )}
      {/* Status bar */}
      <div className={`absolute bottom-0 left-0 right-0 h-px transition-all duration-500 ${file ? "bg-accent" : "bg-border"}`} />
    </div>
  )
}

export function UploadPanel({
  iocFile, setIocFile,
  topImage, setTopImage,
  sideImage, setSideImage,
  parts, setParts,
  onRun, isProcessing, canRun, statusText
}: UploadPanelProps) {
  const [newPart, setNewPart] = useState("")

  const onDropIoc = useCallback((acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.filter(f => f.name.toLowerCase().endsWith('.ioc'))
    if (validFiles.length > 0) setIocFile(validFiles[0])
  }, [setIocFile])

  const { getRootProps: getIocRootProps, getInputProps: getIocInputProps, isDragActive: isIocDragActive } = useDropzone({
    onDrop: onDropIoc,
    accept: { "application/octet-stream": [".ioc"], "text/plain": [".ioc"] },
    maxFiles: 1
  })

  const handleAddPart = (e: React.FormEvent) => {
    e.preventDefault()
    if (newPart.trim()) {
      setParts(prev => [...prev, newPart.trim()])
      setNewPart("")
    }
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Section header */}
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-accent">01 / Inputs</span>
        <h2 className="mt-2 font-[family-name:var(--font-bebas)] text-4xl tracking-tight text-foreground">
          UPLOAD FILES
        </h2>
      </div>

      <div className="h-px bg-border" />

      {/* A — IOC File */}
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-3 block">
          A / STM32 Configuration
        </span>
        <div
          {...getIocRootProps()}
          className={`relative border p-6 cursor-pointer transition-all duration-300 group ${
            isIocDragActive ? "border-accent bg-accent/5"
            : iocFile ? "border-accent/50 bg-accent/5"
            : "border-border hover:border-accent/40 bg-card"
          }`}
        >
          <input {...getIocInputProps()} />
          {iocFile ? (
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 border border-accent/40 flex items-center justify-center bg-accent/10">
                <CheckCircle2 className="w-5 h-5 text-accent" />
              </div>
              <div>
                <p className="font-mono text-sm text-foreground">{iocFile.name}</p>
                <p className="font-mono text-[10px] text-muted-foreground mt-0.5">{(iocFile.size / 1024).toFixed(1)} KB</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); setIocFile(null) }}
                className="ml-auto bg-background/80 hover:bg-accent hover:text-accent-foreground border border-border p-1 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 border border-border flex items-center justify-center group-hover:border-accent/40 transition-colors">
                <FileCode className="w-5 h-5 text-muted-foreground" />
              </div>
              <div>
                <p className="font-mono text-sm text-foreground">Drop .ioc file here</p>
                <p className="font-mono text-[10px] text-muted-foreground mt-0.5">or click to browse</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* B — Two image slots side by side */}
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-3 block">
          B / Breadboard Photos
        </span>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <ArrowUp className="w-3 h-3 text-accent" />
              <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">Top View</span>
            </div>
            <ImageDropZone
              label="Top-down photo"
              hint="Shoot from above"
              file={topImage}
              onDrop={([f]) => setTopImage(f)}
              onClear={() => setTopImage(null)}
              Icon={ImageIcon}
            />
          </div>
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <ArrowRight className="w-3 h-3 text-accent" />
              <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">Side View</span>
            </div>
            <ImageDropZone
              label="Side profile photo"
              hint="Shoot from the side"
              file={sideImage}
              onDrop={([f]) => setSideImage(f)}
              onClear={() => setSideImage(null)}
              Icon={ImageIcon}
            />
          </div>
        </div>
        {/* Progress indicator */}
        <div className="mt-3 flex items-center gap-2">
          <div className={`flex-1 h-px transition-colors duration-300 ${topImage ? "bg-accent" : "bg-border"}`} />
          <span className="font-mono text-[9px] text-muted-foreground">
            {topImage && sideImage ? "2/2 ✓" : topImage || sideImage ? "1/2" : "0/2"}
          </span>
          <div className={`flex-1 h-px transition-colors duration-300 ${sideImage ? "bg-accent" : "bg-border"}`} />
        </div>
      </div>

      {/* C — Component Manifest */}
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-3 block">
          C / Component Manifest (BOM)
        </span>
        <div className="border border-border bg-card p-5 flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <Package className="w-4 h-4 text-accent" />
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
              Specify parts to boost AI accuracy
            </span>
          </div>
          <form onSubmit={handleAddPart} className="flex gap-2">
            <input
              type="text"
              value={newPart}
              onChange={(e) => setNewPart(e.target.value)}
              placeholder="e.g. 555 Timer, L7805, 10uF Cap..."
              className="flex-1 bg-background border border-border focus:border-accent px-3 py-2 font-mono text-sm text-foreground outline-none transition-colors"
            />
            <button
              type="submit"
              className="bg-accent text-accent-foreground px-3 py-2 transition-opacity hover:opacity-80"
            >
              <Plus className="w-4 h-4" />
            </button>
          </form>
          <div className="flex flex-wrap gap-2 min-h-[28px]">
            {parts.length === 0 ? (
              <span className="font-mono text-xs text-muted-foreground/60 italic">No parts listed yet</span>
            ) : (
              parts.map((part, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1.5 px-2 py-1 border border-accent/30 bg-accent/5 font-mono text-[10px] text-accent uppercase tracking-widest"
                >
                  {part}
                  <button onClick={() => setParts(prev => prev.filter((_, idx) => idx !== i))} className="hover:text-foreground transition-colors">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Run Button */}
      <button
        onClick={onRun}
        disabled={!canRun}
        className={`w-full py-4 flex items-center justify-center gap-3 border font-mono text-sm uppercase tracking-[0.2em] transition-all duration-300 ${
          !canRun
            ? "border-border/30 text-muted-foreground/30 cursor-not-allowed bg-card"
            : isProcessing
            ? "border-accent/50 text-accent bg-accent/5 cursor-wait"
            : "border-accent text-accent-foreground bg-accent hover:opacity-90"
        }`}
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>{statusText || "Processing..."}</span>
          </>
        ) : (
          <>
            <UploadCloud className="w-4 h-4" />
            <ScrambleTextOnHover text="Run AI Reconciliation" duration={0.5} />
          </>
        )}
      </button>
    </div>
  )
}
