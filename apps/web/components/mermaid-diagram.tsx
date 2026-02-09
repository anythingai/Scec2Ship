"use client"

import { useEffect, useState } from "react"

interface MermaidDiagramProps {
  chart: string
  className?: string
}

export function MermaidDiagram({ chart, className = "" }: MermaidDiagramProps) {
  const [svg, setSvg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!chart?.trim()) return
    let cancelled = false
    setError(null)
    setSvg(null)
    import("mermaid")
      .then(({ default: mermaid }) => {
        if (cancelled) return
        mermaid.initialize({
          startOnLoad: false,
          theme: "neutral",
          securityLevel: "loose",
        })
        const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2)}`
        mermaid
          .render(id, chart.trim())
          .then(({ svg: result }) => {
            if (!cancelled) setSvg(result)
          })
          .catch((err) => {
            if (!cancelled) setError(String(err?.message || err))
          })
      })
    return () => { cancelled = true }
  }, [chart])

  if (error) {
    return (
      <div className={`rounded-lg border border-border bg-secondary/30 p-4 ${className}`}>
        <p className="text-xs text-destructive mb-2">Could not render diagram</p>
        <pre className="text-xs font-mono overflow-x-auto whitespace-pre-wrap text-muted-foreground">
          {chart}
        </pre>
        <p className="mt-2 text-[10px] text-muted-foreground">
          Paste at <a href="https://mermaid.live" target="_blank" rel="noreferrer" className="text-primary underline">mermaid.live</a> to render.
        </p>
      </div>
    )
  }

  if (svg) {
    return (
      <div
        className={`mermaid-diagram overflow-auto rounded-lg border border-border bg-white p-4 ${className}`}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    )
  }

  return (
    <div className={`rounded-lg border border-border bg-secondary/30 p-4 animate-pulse ${className}`}>
      <div className="h-40 flex items-center justify-center text-muted-foreground text-xs">
        Rendering diagram…
      </div>
    </div>
  )
}
