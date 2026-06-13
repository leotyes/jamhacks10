import { Loader2, UploadCloud, FileCode, Image as ImageIcon, CheckCircle2, Plus, X, Package } from "lucide-react"
import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { ScrambleTextOnHover } from "./ScrambleText"

interface UploadPanelProps {
  iocFile: File | null
  setIocFile: (file: File | null) => void
  sideImageFile: File | null
  setSideImageFile: (file: File | null) => void
  topImageFile: File | null
  setTopImageFile: (file: File | null) => void
  parts: string[]
  setParts: React.Dispatch<React.SetStateAction<string[]>>
  onRun: () => void
  isProcessing: boolean
  statusText: string
}

function ImageDropZone({
  label,
  file,
  onDrop,
}: {
  label: string
  file: File | null
  onDrop: (files: File[]) => void
}) {
  const [preview, setPreview] = useState<string | null>(null)

  const handleDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        const f = acceptedFiles[0]
        onDrop([f])
        setPreview(URL.createObjectURL(f))
      }
    },
    [onDrop]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleDrop,
    accept: { "image/*": [".jpeg", ".jpg", ".png", ".webp"] },
    maxFiles: 1,
  })

  return (
    <div className="flex-1 min-w-0">
      <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2 block">
        {label}
      </span>
      <div
        {...getRootProps()}
        className={`relative border cursor-pointer transition-all duration-300 group overflow-hidden min-h-[120px] ${isDragActive
          ? "border-accent bg-accent/5"
          : file
            ? "border-accent/50"
            : "border-border hover:border-accent/40 bg-card"
          }`}
      >
        <input {...getInputProps()} />
        {preview ? (
          <>
            <img src={preview} alt="Preview" className="w-full h-28 object-cover opacity-50" />
            <div className="absolute inset-0 flex items-center justify-center bg-background/60 backdrop-blur-sm">
              <div className="flex flex-col items-center gap-1.5 px-2 text-center">
                <CheckCircle2 className="w-4 h-4 text-accent shrink-0" />
                <p className="font-mono text-[10px] text-foreground leading-tight break-all">{file?.name}</p>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 p-4 h-[120px]">
            <div className="w-8 h-8 border border-border flex items-center justify-center group-hover:border-accent/40 transition-colors">
              <ImageIcon className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="text-center">
              <p className="font-mono text-xs text-foreground">Drop photo here</p>
              <p className="font-mono text-[10px] text-muted-foreground mt-0.5">JPEG · PNG · WEBP</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export function UploadPanel({
  iocFile, setIocFile,
  sideImageFile, setSideImageFile,
  topImageFile, setTopImageFile,
  parts, setParts, onRun, isProcessing, statusText,
}: UploadPanelProps) {
  const [newPart, setNewPart] = useState("")

  const onDropIoc = useCallback((acceptedFiles: File[]) => {
    const valid = acceptedFiles.filter(f => f.name.toLowerCase().endsWith(".ioc"))
    if (valid.length > 0) setIocFile(valid[0])
  }, [setIocFile])

  const { getRootProps: getIocRootProps, getInputProps: getIocInputProps, isDragActive: isIocDragActive } = useDropzone({
    onDrop: onDropIoc,
    accept: { "application/octet-stream": [".ioc"], "text/plain": [".ioc"] },
    maxFiles: 1,
  })

  const handleAddPart = (e: React.FormEvent) => {
    e.preventDefault()
    if (newPart.trim()) {
      setParts(prev => [...prev, newPart.trim()])
      setNewPart("")
    }
  }

  const formatFileSize = (bytes: number) => (bytes / 1024).toFixed(1) + " KB"

  const canRun = iocFile && sideImageFile && topImageFile && !isProcessing

  return (
    <div className="flex flex-col gap-8">
      {/* Section header */}
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-accent">01 / Inputs</span>
        <h2 className="mt-2 font-[family-name:var(--font-bebas)] text-4xl tracking-tight text-foreground">
          UPLOAD FILES
        </h2>
      </div>

      {/* Divider */}
      <div className="h-px bg-border" />

      {/* IOC Drop Zone */}
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-3 block">
          A / STM32 Configuration
        </span>
        <div
          {...getIocRootProps()}
          className={`relative border p-6 cursor-pointer transition-all duration-300 group ${isIocDragActive
            ? "border-accent bg-accent/5"
            : iocFile
              ? "border-accent/50 bg-accent/5"
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
                <p className="font-mono text-[10px] text-muted-foreground mt-0.5">{formatFileSize(iocFile.size)}</p>
              </div>
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

      {/* Image Drop Zones — side by side */}
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-3 block">
          B / Board Photos
        </span>
        <div className="flex gap-3">
          <ImageDropZone
            label="Side View"
            file={sideImageFile}
            onDrop={([f]) => setSideImageFile(f)}
          />
          <ImageDropZone
            label="Top View"
            file={topImageFile}
            onDrop={([f]) => setTopImageFile(f)}
          />
        </div>
      </div>

      {/* Parts Manifest */}
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
        className={`w-full py-4 flex items-center justify-center gap-3 border font-mono text-sm uppercase tracking-[0.2em] transition-all duration-300 ${!iocFile || !sideImageFile || !topImageFile
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
