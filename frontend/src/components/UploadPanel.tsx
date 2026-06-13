import { Loader2, UploadCloud, FileCode, Image as ImageIcon, CheckCircle2, Plus, X, Package } from "lucide-react"
import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { ScrambleTextOnHover } from "./ScrambleText"

interface UploadPanelProps {
  iocFile: File | null
  setIocFile: (file: File | null) => void
  imageFile: File | null
  setImageFile: (file: File | null) => void
  parts: string[]
  setParts: React.Dispatch<React.SetStateAction<string[]>>
  onRun: () => void
  isProcessing: boolean
  statusText: string
}

export function UploadPanel({
  iocFile, setIocFile, imageFile, setImageFile,
  parts, setParts, onRun, isProcessing, statusText
}: UploadPanelProps) {
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [newPart, setNewPart] = useState("")

  const onDropIoc = useCallback((acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.filter(file => file.name.toLowerCase().endsWith('.ioc'))
    if (validFiles.length > 0) {
      setIocFile(validFiles[0])
    }
  }, [setIocFile])

  const onDropImage = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]
      setImageFile(file)
      setImagePreview(URL.createObjectURL(file))
    }
  }, [setImageFile])

  const { getRootProps: getIocRootProps, getInputProps: getIocInputProps, isDragActive: isIocDragActive } = useDropzone({
    onDrop: onDropIoc,
    accept: {
      "application/octet-stream": [".ioc"],
      "text/plain": [".ioc"]
    },
    maxFiles: 1
  })

  const { getRootProps: getImageRootProps, getInputProps: getImageInputProps, isDragActive: isImageDragActive } = useDropzone({
    onDrop: onDropImage,
    accept: { "image/*": [".jpeg", ".jpg", ".png"] },
    maxFiles: 1
  })

  const handleAddPart = (e: React.FormEvent) => {
    e.preventDefault()
    if (newPart.trim()) {
      setParts(prev => [...prev, newPart.trim()])
      setNewPart("")
    }
  }

  const formatFileSize = (bytes: number) => (bytes / 1024).toFixed(1) + " KB"

  const canRun = iocFile && imageFile && !isProcessing

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
          className={`relative border p-6 cursor-pointer transition-all duration-300 group ${
            isIocDragActive
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

      {/* Image Drop Zone */}
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-3 block">
          B / Breadboard Photo
        </span>
        <div
          {...getImageRootProps()}
          className={`relative border cursor-pointer transition-all duration-300 group overflow-hidden min-h-[140px] ${
            isImageDragActive
              ? "border-accent bg-accent/5"
              : imageFile
              ? "border-accent/50"
              : "border-border hover:border-accent/40 bg-card"
          }`}
        >
          <input {...getImageInputProps()} />
          {imagePreview ? (
            <>
              <img src={imagePreview} alt="Preview" className="w-full h-36 object-cover opacity-50" />
              <div className="absolute inset-0 flex items-center justify-center bg-background/60 backdrop-blur-sm">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-accent" />
                  <p className="font-mono text-sm text-foreground">{imageFile?.name}</p>
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-4 p-6">
              <div className="w-10 h-10 border border-border flex items-center justify-center group-hover:border-accent/40 transition-colors">
                <ImageIcon className="w-5 h-5 text-muted-foreground" />
              </div>
              <div>
                <p className="font-mono text-sm text-foreground">Drop breadboard photo here</p>
                <p className="font-mono text-[10px] text-muted-foreground mt-0.5">JPEG or PNG</p>
              </div>
            </div>
          )}
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
        className={`w-full py-4 flex items-center justify-center gap-3 border font-mono text-sm uppercase tracking-[0.2em] transition-all duration-300 ${
          !iocFile || !imageFile
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
