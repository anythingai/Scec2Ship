"use client"

import React, { useState, useRef, useEffect, useCallback } from "react"
import type { RunState, RunSummary } from "@/lib/types"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MermaidDiagram } from "./mermaid-diagram"
import { RunSummaryCard } from "./run-summary"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || (typeof window !== "undefined" ? window.location.origin : "")

function CollaborationPanel({ runId, onApproveRun }: { runId: string; onApproveRun: (approved: boolean) => void }) {
  const [comments, setComments] = useState<Array<{ comment_id: string; text: string; author: string; created_at: string }>>([])
  const [newComment, setNewComment] = useState("")
  const loadComments = useCallback(async () => {
    const res = await fetch(`${API_BASE}/runs/${runId}/comments`)
    if (res.ok) {
      const d = await res.json()
      setComments(d.comments || [])
    }
  }, [runId])
  useEffect(() => {
    const ac = new AbortController()
    fetch(`${API_BASE}/runs/${runId}/comments`, { signal: ac.signal })
      .then((r) => (r.ok ? r.json() : { comments: [] }))
      .then((d) => setComments(d.comments || []))
      .catch(() => {})
    return () => ac.abort()
  }, [runId])
  const addComment = async () => {
    if (!newComment.trim()) return
    await fetch(`${API_BASE}/runs/${runId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: newComment.trim() }),
    })
    setNewComment("")
    loadComments()
  }
  return (
    <div className="border-b border-primary/30 bg-primary/5 px-4 py-3 space-y-3">
      <div className="flex items-center justify-between gap-4">
        <div className="text-sm font-medium text-foreground">
          PRD & design ready for review. Approve to continue or request changes.
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs border-destructive/30 text-destructive hover:bg-destructive/10"
            onClick={() => onApproveRun(false)}
          >
            Request Changes
          </Button>
          <Button size="sm" className="h-8 text-xs" onClick={() => onApproveRun(true)}>
            Approve
          </Button>
        </div>
      </div>
      <div className="border-t border-border pt-2">
        <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Comments</div>
        <div className="space-y-1 max-h-24 overflow-y-auto">
          {comments.map((c) => (
            <div key={c.comment_id} className="text-xs rounded bg-secondary/50 px-2 py-1">
              <span className="text-muted-foreground">{c.author}: </span>
              <span className="text-foreground">{c.text}</span>
            </div>
          ))}
        </div>
        <div className="flex gap-2 mt-2">
          <input
            type="text"
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add comment..."
            className="flex-1 h-7 rounded border border-border bg-background px-2 text-xs"
            onKeyDown={(e) => e.key === "Enter" && addComment()}
          />
          <Button size="sm" className="h-7 text-xs" onClick={addComment} disabled={!newComment.trim()}>
            Add
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            onClick={async () => {
              const res = await fetch(`${API_BASE}/runs/${runId}/comments/resolve`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ apply: true }),
              })
              const d = await res.json()
              if (d.status === "applied") {
                alert(`PRD updated: ${d.suggestion}`)
                window.location.reload()
              } else if (d.suggestion) alert(`Suggestion: ${d.suggestion}`)
              else if (d.message) alert(d.message)
            }}
          >
            AI Resolve & Apply
          </Button>
        </div>
      </div>
    </div>
  )
}

function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split("\n")
  const failureRef = useRef<HTMLDivElement>(null)
  const hasFailures = content.toLowerCase().includes("fail") || content.toLowerCase().includes("error")
  
  // Compute first failure index during render
  const firstFailureIndex = hasFailures ? lines.findIndex((line) => {
    const isFailure = line.toLowerCase().includes("fail") || line.toLowerCase().includes("error") || (line.toLowerCase().includes("exit code") && !line.includes("0"))
    const isTestName = /test_\w+|def test_/.test(line)
    return isFailure || (isTestName && hasFailures)
  }) : -1
  
  useEffect(() => {
    if (hasFailures && failureRef.current) {
      failureRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [hasFailures])
  
  return (
    <div className="space-y-1 p-4">
      {lines.map((line, i) => {
        const isFailure = line.toLowerCase().includes("fail") || line.toLowerCase().includes("error") || (line.toLowerCase().includes("exit code") && !line.includes("0"))
        const isTestName = /test_\w+|def test_/.test(line)
        const isFailureLine = isFailure || (isTestName && hasFailures)
        
        if (line.startsWith("# ")) return <h1 key={i} className="text-xl font-bold text-foreground mt-4 mb-2">{line.slice(2)}</h1>
        if (line.startsWith("## ")) {
          const isFailureSection = line.toLowerCase().includes("fail") || line.toLowerCase().includes("error")
          return (
            <h2 
              key={i} 
              ref={isFailureSection && firstFailureIndex === i ? failureRef : undefined}
              className={`text-lg font-semibold mt-4 mb-1 ${isFailureSection ? "text-destructive" : "text-foreground"}`}
            >
              {line.slice(3)}
            </h2>
          )
        }
        if (line.startsWith("### ")) return <h3 key={i} className="text-sm font-semibold text-foreground mt-3 mb-1">{line.slice(4)}</h3>
        if (line.startsWith("- [ ] ")) return (
          <div key={i} className="flex items-start gap-2 text-sm text-muted-foreground pl-2">
            <div className="mt-1 h-3.5 w-3.5 shrink-0 rounded-sm border border-border" />
            <span>{line.slice(6)}</span>
          </div>
        )
        if (line.startsWith("- [PASS]")) return (
          <div key={i} className="flex items-start gap-2 text-sm pl-2">
            <span className="mt-0.5 shrink-0 text-success font-mono text-xs">[PASS]</span>
            <span className="text-foreground">{line.slice(8).trim()}</span>
          </div>
        )
        if (line.startsWith("- [FAIL]") || isFailureLine) {
          return (
            <div 
              key={i} 
              ref={firstFailureIndex === i ? failureRef : undefined}
              className={`flex items-start gap-2 text-sm pl-2 rounded-md p-2 ${
                isFailureLine ? "bg-destructive/10 border border-destructive/20" : ""
              }`}
            >
              <span className="mt-0.5 shrink-0 text-destructive font-mono text-xs font-bold">[FAIL]</span>
              <span className="text-destructive font-semibold">{line.startsWith("- [FAIL]") ? line.slice(8).trim() : line}</span>
            </div>
          )
        }
        if (line.startsWith("- ")) return (
          <div key={i} className="flex items-start gap-2 text-sm text-muted-foreground pl-2">
            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/50" />
            <span>{line.slice(2)}</span>
          </div>
        )
        if (line.startsWith("---")) return <hr key={i} className="border-border my-3" />
        if (line.startsWith("```")) return <div key={i} className="bg-secondary/50 rounded px-2 py-0.5 font-mono text-[10px] text-muted-foreground" />
        if (line.startsWith("|")) {
          const cells = line.split("|").filter(Boolean).map((c) => c.trim())
          if (cells.every((c) => /^[-:]+$/.test(c))) return null
          return (
            <div key={i} className="flex gap-2 font-mono text-xs">
              {cells.map((cell, ci) => (
                <span key={ci} className="flex-1 text-muted-foreground truncate">{cell}</span>
              ))}
            </div>
          )
        }
        if (line.trim() === "") return <div key={i} className="h-2" />
        const formatted = line.replace(/\*\*([^*]+)\*\*/g, '<strong class="text-foreground font-medium">$1</strong>')
        return (
          <p 
            key={i} 
            className={`text-sm leading-relaxed ${
              isFailureLine ? "text-destructive font-semibold bg-destructive/5 rounded px-2 py-1" : "text-muted-foreground"
            }`}
            dangerouslySetInnerHTML={{ __html: formatted }} 
          />
        )
      })}
    </div>
  )
}

function TicketsTable({ tickets }: { tickets: NonNullable<RunState["artifacts"]["tickets"]> }) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const riskColors = {
    low: "bg-success/10 text-success border-success/20",
    med: "bg-warning/10 text-warning border-warning/20",
    high: "bg-destructive/10 text-destructive border-destructive/20",
  }

  return (
    <div className="p-4">
      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/50">
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">ID</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Title</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Risk</th>
              <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Est.</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Owner</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((ticket, idx) => (
              <React.Fragment key={ticket.id}>
                <tr
                  className={`border-b border-border/50 cursor-pointer transition-colors hover:bg-secondary/30 ${idx % 2 === 0 ? "" : "bg-secondary/20"}`}
                  onClick={() => setExpandedId(expandedId === ticket.id ? null : ticket.id)}
                >
                  <td className="px-3 py-2 font-mono text-xs text-primary">{ticket.id}</td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1.5">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`shrink-0 transition-transform ${expandedId === ticket.id ? "rotate-90" : ""} text-muted-foreground`}>
                        <polyline points="9 18 15 12 9 6" />
                      </svg>
                      <span className="text-xs font-medium text-foreground">{ticket.title}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant="outline" className={`text-[10px] ${riskColors[ticket.risk_level]}`}>
                      {ticket.risk_level}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-muted-foreground">{ticket.estimate_hours}h</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">{ticket.owner || "Unassigned"}</td>
                </tr>
                {expandedId === ticket.id && (
                  <tr className="bg-secondary/10">
                    <td colSpan={5} className="px-6 py-3">
                      <p className="text-xs text-muted-foreground mb-2">{ticket.description}</p>
                      <div className="space-y-2">
                        <div>
                          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Acceptance Criteria</span>
                          <ul className="mt-1 space-y-0.5">
                            {ticket.acceptance_criteria.map((ac, j) => (
                              <li key={j} className="flex items-start gap-1.5 text-xs text-foreground">
                                <div className="mt-1 h-3 w-3 shrink-0 rounded-sm border border-border" />
                                {ac}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Expected Files</span>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {ticket.files_expected.map((f) => (
                              <span key={f} className="rounded bg-secondary px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{f}</span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>{tickets.length} tickets</span>
        <span>Total: {tickets.reduce((sum, t) => sum + t.estimate_hours, 0)}h estimated</span>
      </div>
    </div>
  )
}

function EvidenceMapView({
  evidenceMap,
  showCitations,
}: {
  evidenceMap: NonNullable<RunState["artifacts"]["evidenceMap"]>
  showCitations: boolean
}) {
  return (
    <div className="space-y-6 p-4">
      {/* Why This Feature */}
      {evidenceMap.featureChoice && (
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
          <div className="flex items-center gap-2 mb-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Why This Feature</span>
          </div>
          <h3 className="text-base font-semibold text-foreground">{evidenceMap.featureChoice.feature}</h3>
          <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{evidenceMap.featureChoice.rationale}</p>
          <div className="mt-2 flex gap-1">
            {evidenceMap.featureChoice.linked_claim_ids.map((id) => (
              <span key={id} className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] text-primary">{id}</span>
            ))}
          </div>
        </div>
      )}

      {/* Top 3 Candidates */}
      {evidenceMap.topFeatures.length > 1 && (
        <div>
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">All Candidates</h3>
          <div className="space-y-2">
            {evidenceMap.topFeatures.map((f, i) => {
              const isSelected = evidenceMap.featureChoice?.feature === f.feature
              return (
                <div key={f.feature} className={`rounded border p-3 ${isSelected ? "border-primary/30 bg-primary/5" : "border-border"}`}>
                  <div className="flex items-center gap-2">
                    <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${isSelected ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground"}`}>
                      {i + 1}
                    </span>
                    <span className="text-xs font-medium text-foreground">{f.feature}</span>
                    {isSelected && <Badge variant="outline" className="text-[9px] border-primary/30 text-primary px-1">Selected</Badge>}
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground pl-7">{f.rationale}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Claims */}
      <div>
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Evidence Claims</h3>
        <div className="space-y-3">
          {evidenceMap.claims.map((claim) => (
            <div key={claim.claim_id} className="rounded-lg border border-border p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-secondary px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{claim.claim_id}</span>
                  <span className="text-sm font-medium text-foreground">{claim.claim_text}</span>
                </div>
                <span className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[10px] ${
                  claim.confidence >= 0.8
                    ? "bg-success/10 text-success"
                    : claim.confidence >= 0.6
                      ? "bg-warning/10 text-warning"
                      : "bg-secondary text-muted-foreground"
                }`}>
                  {Math.round(claim.confidence * 100)}%
                </span>
              </div>
              {showCitations && (
                <div className="mt-2 space-y-1">
                  {claim.supporting_sources.map((src, i) => (
                    <div key={i} className="flex items-start gap-2 rounded bg-secondary/50 px-2 py-1.5">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mt-0.5 shrink-0 text-muted-foreground">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <div className="flex-1 min-w-0">
                        <span className="font-mono text-[10px] text-muted-foreground">{src.file}:{src.line_range[0]}-{src.line_range[1]}</span>
                        <p className="text-xs text-foreground/80 italic">{`"${src.quote}"`}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function DiffViewer({ diff }: { diff: string }) {
  const lines = diff.split("\n")
  return (
    <div className="p-4">
      <div className="rounded-lg border border-border overflow-hidden bg-secondary/30">
        <div className="overflow-x-auto">
          <pre className="text-xs leading-5">
            {lines.map((line, i) => {
              let lineClass = "text-muted-foreground"
              let bgClass = ""
              if (line.startsWith("+") && !line.startsWith("+++")) {
                lineClass = "text-success"
                bgClass = "bg-success/5"
              } else if (line.startsWith("-") && !line.startsWith("---")) {
                lineClass = "text-destructive"
                bgClass = "bg-destructive/5"
              } else if (line.startsWith("@@")) {
                lineClass = "text-primary"
                bgClass = "bg-primary/5"
              } else if (line.startsWith("diff") || line.startsWith("index") || line.startsWith("---") || line.startsWith("+++")) {
                lineClass = "text-muted-foreground font-semibold"
              }
              return (
                <div key={i} className={`flex ${bgClass}`}>
                  <span className="w-10 shrink-0 select-none text-right pr-3 text-muted-foreground/30">{i + 1}</span>
                  <code className={`flex-1 px-2 font-mono ${lineClass}`}>{line || " "}</code>
                </div>
              )
            })}
          </pre>
        </div>
      </div>
    </div>
  )
}

function EmptyTab({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="h-10 w-10 rounded-full border border-border flex items-center justify-center mb-3">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted-foreground/40">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <p className="text-sm font-medium text-muted-foreground">{title}</p>
      <p className="mt-1 text-xs text-muted-foreground/60">{description}</p>
    </div>
  )
}

const CONNECTOR_SOURCES = ["gong", "intercom", "linear", "posthog", "slack"]

interface ArtifactsPanelProps {
  artifacts: RunState["artifacts"]
  status: RunState["status"]
  isPrMode: boolean
  showCitations: boolean
  onToggleCitations: () => void
  summary: RunSummary | null
  failureMessage: string | null
  runId?: string | null
  onApproveRun?: (approved: boolean) => void
  onRefreshArtifacts?: (runId: string) => Promise<void>
  linearUrl?: string | null
  jiraUrl?: string | null
}

export function ArtifactsPanel({
  artifacts,
  status,
  isPrMode,
  showCitations,
  onToggleCitations,
  summary,
  failureMessage,
  runId,
  onApproveRun,
  onRefreshArtifacts,
  linearUrl,
  jiraUrl,
}: ArtifactsPanelProps) {
  const [copyMessage, setCopyMessage] = useState<string | null>(null)
  const hasAnyArtifact = artifacts.prd || artifacts.wireframes || artifacts.tickets || artifacts.evidenceMap || artifacts.diff || artifacts.testReport
  const isTerminal = status === "completed" || status === "failed"
  const canOpenPr = Boolean(summary?.prUrl)
  const downloadUrl = runId ? `${API_BASE}/runs/${runId}/artifacts/zip` : null
  const origin = typeof window !== "undefined" ? window.location.origin : API_BASE
  const shareUrl = runId ? `${origin}/runs/${runId}/artifacts` : `${origin}/runs/latest/artifacts`

  const handleCopyLink = () => {
    // Generate comprehensive shareable link with both run view and artifact download
    const baseUrl = typeof window !== "undefined" ? window.location.origin : API_BASE
    const runViewUrl = runId ? `${baseUrl}/runs/${runId}` : shareUrl
    const artifactZipUrl = runId ? `${baseUrl}/runs/${runId}/artifacts/zip` : null
    
    // Create shareable text with both URLs
    const shareableText = artifactZipUrl
      ? `Growpad Run: ${runId}\n\nView Run: ${runViewUrl}\nDownload Artifacts: ${artifactZipUrl}`
      : `Growpad Run: ${runViewUrl}`
    
    navigator.clipboard.writeText(shareableText).then(() => {
      setCopyMessage("Link copied!")
      setTimeout(() => setCopyMessage(null), 2000)
    }).catch(() => {
      // Fallback: just copy the run URL
      navigator.clipboard.writeText(runViewUrl).then(() => {
        setCopyMessage("Link copied!")
        setTimeout(() => setCopyMessage(null), 2000)
      })
    })
  }

  const isAwaitingApproval = status === "awaiting_approval"

  return (
    <div className="flex h-full flex-col">
      {isAwaitingApproval && onApproveRun && runId && (
        <CollaborationPanel runId={runId} onApproveRun={onApproveRun} />
      )}
      {artifacts.deviationAlert && runId && (
        <div className="mx-4 mt-3 flex items-center justify-between gap-3 rounded-lg border border-warning/40 bg-warning/5 px-4 py-3">
          <p className="text-xs text-foreground">{artifacts.deviationAlert.message}</p>
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs shrink-0 border-warning/40 text-warning hover:bg-warning/10"
            onClick={async () => {
              const res = await fetch(`${API_BASE}/runs/${runId}/update-prd-from-deviation`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
              })
              const d = await res.json()
              if (d.status === "updated" && onRefreshArtifacts) {
                await onRefreshArtifacts(runId)
              } else if (d.message) alert(d.message)
            }}
          >
            Update PRD
          </Button>
        </div>
      )}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Artifacts</h2>
        <div className="flex items-center gap-2">
          {/* Citations toggle */}
          {artifacts.evidenceMap && (
            <button
              type="button"
              onClick={onToggleCitations}
              className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-[10px] font-medium transition-colors ${
                showCitations ? "bg-primary/10 text-primary" : "bg-secondary text-muted-foreground hover:text-foreground"
              }`}
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              Citations {showCitations ? "ON" : "OFF"}
            </button>
          )}
          {/* Copy link */}
          {hasAnyArtifact && (
            <button
              type="button"
              onClick={handleCopyLink}
              className="flex items-center gap-1.5 rounded-md bg-secondary px-2 py-1 text-[10px] font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              {copyMessage || "Copy Link"}
            </button>
          )}
          {/* Open PR button */}
          {isPrMode && isTerminal && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs gap-1.5 bg-transparent border-success/30 text-success hover:bg-success/10"
              onClick={() => {
                if (summary?.prUrl) window.open(summary.prUrl, "_blank")
              }}
              disabled={!canOpenPr}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="18" cy="18" r="3" />
                <circle cx="6" cy="6" r="3" />
                <path d="M13 6h3a2 2 0 0 1 2 2v7" />
                <line x1="6" y1="9" x2="6" y2="21" />
              </svg>
              {canOpenPr ? "Open PR" : "PR unavailable"}
            </Button>
          )}
          {/* Generate .cursorrules - download if available */}
          {runId && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs gap-1.5 bg-transparent"
              onClick={() => {
                if (runId) window.open(`${API_BASE}/runs/${runId}/artifacts/.cursorrules`, "_blank")
              }}
              disabled={!runId}
              title="Download .cursorrules for Cursor/Windsurf"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              .cursorrules
            </Button>
          )}
          {/* Download zip */}
          {hasAnyArtifact && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs gap-1.5 bg-transparent"
              onClick={() => {
                if (downloadUrl) window.open(downloadUrl, "_blank")
              }}
              disabled={!downloadUrl}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download Zip
            </Button>
          )}
        </div>
      </div>

      <Tabs defaultValue="prd" className="flex flex-1 flex-col overflow-hidden">
        <TabsList className="mx-4 mt-2 h-8 bg-secondary/50 p-0.5 flex-wrap">
          <TabsTrigger value="prd" className="text-xs h-7 data-[state=active]:bg-card">PRD</TabsTrigger>
          <TabsTrigger value="wireframes" className="text-xs h-7 data-[state=active]:bg-card">Wireframes</TabsTrigger>
          <TabsTrigger value="userFlow" className="text-xs h-7 data-[state=active]:bg-card">User Flow</TabsTrigger>
          <TabsTrigger value="tickets" className="text-xs h-7 data-[state=active]:bg-card">Tickets</TabsTrigger>
          <TabsTrigger value="evidence" className="text-xs h-7 data-[state=active]:bg-card">Evidence</TabsTrigger>
          <TabsTrigger value="diff" className="text-xs h-7 data-[state=active]:bg-card">Diff</TabsTrigger>
          <TabsTrigger value="tests" className="text-xs h-7 data-[state=active]:bg-card">Tests</TabsTrigger>
          <TabsTrigger value="audit" className="text-xs h-7 data-[state=active]:bg-card">Audit</TabsTrigger>
          {artifacts.decisionMemo && <TabsTrigger value="decisionMemo" className="text-xs h-7 data-[state=active]:bg-card">Decision Memo</TabsTrigger>}
          {artifacts.goToMarket && <TabsTrigger value="goToMarket" className="text-xs h-7 data-[state=active]:bg-card">GTM</TabsTrigger>}
          {artifacts.analyticsSpec && <TabsTrigger value="analyticsSpec" className="text-xs h-7 data-[state=active]:bg-card">Analytics</TabsTrigger>}
          {summary && <TabsTrigger value="summary" className="text-xs h-7 data-[state=active]:bg-card">Summary</TabsTrigger>}
        </TabsList>

        <ScrollArea className="flex-1">
          <TabsContent value="prd" className="mt-0">
            {artifacts.prd ? <MarkdownRenderer content={artifacts.prd} /> : <EmptyTab title="No PRD yet" description="PRD will appear after the Generate PRD stage completes" />}
          </TabsContent>

          <TabsContent value="wireframes" className="mt-0">
            {artifacts.wireframes ? (
              <div className="p-4">
                <div className="rounded-lg border border-border overflow-hidden bg-background">
                  <iframe
                    srcDoc={artifacts.wireframes}
                    title="Wireframes"
                    className="w-full min-h-[400px] border-0"
                    sandbox="allow-same-origin"
                  />
                </div>
              </div>
            ) : (
              <EmptyTab title="No wireframes yet" description="Wireframes will appear after the Generate Design stage completes" />
            )}
          </TabsContent>

          <TabsContent value="userFlow" className="mt-0">
            {artifacts.userFlow ? (
              <div className="p-4">
                <MermaidDiagram chart={artifacts.userFlow} />
              </div>
            ) : (
              <EmptyTab title="No user flow yet" description="User flow diagram will appear after the Generate Design stage completes" />
            )}
          </TabsContent>

          <TabsContent value="tickets" className="mt-0">
            {artifacts.tickets ? (
              <div>
                {(linearUrl || jiraUrl) && (
                  <div className="mx-4 mt-2 flex gap-2">
                    {linearUrl && (
                      <a href={linearUrl} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline">
                        Open in Linear →
                      </a>
                    )}
                    {jiraUrl && (
                      <a href={jiraUrl} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline">
                        Open in Jira →
                      </a>
                    )}
                  </div>
                )}
                {artifacts.ticketsEpicTitle && (
                  <div className="border-b border-border px-4 py-3">
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Epic</div>
                    <div className="text-sm font-semibold text-foreground">{artifacts.ticketsEpicTitle}</div>
                  </div>
                )}
                <TicketsTable tickets={artifacts.tickets} />
              </div>
            ) : (
              <EmptyTab title="No tickets yet" description="Tickets will appear after the Generate Tickets stage completes" />
            )}
          </TabsContent>

          <TabsContent value="evidence" className="mt-0">
            {artifacts.evidenceMap ? (
              <div className="space-y-2">
                <div className="mx-4 mt-2 flex flex-wrap gap-2">
                  {artifacts.evidenceMap.claims.some((c) =>
                    c.supporting_sources?.some((s) => String(s.file || "").toLowerCase().includes("competitor"))
                  ) && (
                    <Badge variant="outline" className="text-[10px] border-warning/30 text-warning bg-warning/5">
                      Competitive gap — evidence from competitors analysis
                    </Badge>
                  )}
                  {artifacts.evidenceMap.claims.some((c) =>
                    c.supporting_sources?.some((s) =>
                      CONNECTOR_SOURCES.some((conn) =>
                        String(s.file || "").toLowerCase().includes(conn)
                      )
                    )
                  ) && (
                    <Badge variant="outline" className="text-[10px] border-primary/30 text-primary bg-primary/5">
                      Live connector data
                    </Badge>
                  )}
                </div>
                <EvidenceMapView evidenceMap={artifacts.evidenceMap} showCitations={showCitations} />
              </div>
            ) : (
              <EmptyTab title="No evidence map yet" description="Evidence map will appear after the Synthesize stage completes" />
            )}
          </TabsContent>

          <TabsContent value="diff" className="mt-0">
            {artifacts.diff ? <DiffViewer diff={artifacts.diff} /> : <EmptyTab title="No diff yet" description="Code diff will appear after the Implement stage completes" />}
          </TabsContent>

          <TabsContent value="tests" className="mt-0">
            {artifacts.testReport ? <MarkdownRenderer content={artifacts.testReport} /> : <EmptyTab title="No test report yet" description="Test report will appear after the Verify stage completes" />}
          </TabsContent>

          <TabsContent value="audit" className="mt-0">
            {artifacts.auditTrail ? (
              <div className="p-4 space-y-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Search by feature, claim..."
                    className="flex-1 h-8 rounded-md border border-border bg-secondary/50 px-2 text-xs placeholder:text-muted-foreground"
                    onChange={(e) => {
                      const q = e.target.value.toLowerCase().trim()
                      const el = document.getElementById("audit-search-results")
                      if (el) {
                        const items = el.querySelectorAll("[data-audit-text]")
                        items.forEach((item) => {
                          const text = (item.getAttribute("data-audit-text") || "").toLowerCase()
                          ;(item as HTMLElement).style.display = !q || text.includes(q) ? "" : "none"
                        })
                      }
                    }}
                  />
                  <span className="text-[10px] text-muted-foreground self-center">Audit trail search</span>
                </div>
                <div id="audit-search-results">
                <div className="rounded-lg border border-primary/20 bg-primary/5 p-4" data-audit-text={String(artifacts.auditTrail.feature_choice_rationale ?? "")}>
                  <h3 className="text-sm font-semibold text-foreground">Why did we build this?</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {typeof artifacts.auditTrail.feature_choice_rationale === "string"
                      ? artifacts.auditTrail.feature_choice_rationale
                      : "No rationale captured."}
                  </p>
                </div>
                <div className="rounded-lg border border-border p-4">
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Evidence Sources</h3>
                  <ul className="space-y-1 text-xs">
                    {(artifacts.auditTrail.evidence_sources as Array<{ claim_id?: string; claim_text?: string; confidence?: number }>)?.map((s, i) => (
                      <li key={i} className="flex gap-2" data-audit-text={`${s.claim_id ?? ""} ${s.claim_text ?? ""}`}>
                        <span className="font-mono text-muted-foreground">{s.claim_id}</span>
                        <span className="text-foreground">{s.claim_text}</span>
                        {s.confidence != null && <span className="text-success">{Math.round(s.confidence * 100)}%</span>}
                      </li>
                    )) ?? []}
                  </ul>
                </div>
                <div className="rounded-lg border border-border p-4" data-audit-text={JSON.stringify(artifacts.auditTrail)}>
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Run Details</h3>
                  <pre className="text-[10px] font-mono text-muted-foreground overflow-x-auto">
                    {JSON.stringify(artifacts.auditTrail, null, 2)}
                  </pre>
                </div>
                </div>
              </div>
            ) : (
              <EmptyTab title="No audit trail yet" description="Audit trail will appear after the Export stage completes" />
            )}
          </TabsContent>

          {artifacts.decisionMemo && (
            <TabsContent value="decisionMemo" className="mt-0">
              <div className="p-4">
                <MarkdownRenderer content={artifacts.decisionMemo} />
              </div>
            </TabsContent>
          )}
          {artifacts.goToMarket && (
            <TabsContent value="goToMarket" className="mt-0">
              <div className="p-4">
                <MarkdownRenderer content={artifacts.goToMarket} />
              </div>
            </TabsContent>
          )}
          {artifacts.analyticsSpec && (
            <TabsContent value="analyticsSpec" className="mt-0">
              <div className="p-4">
                <pre className="rounded-lg border border-border bg-secondary/30 p-4 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                  {(() => {
                    try {
                      const parsed = typeof artifacts.analyticsSpec === "string"
                        ? JSON.parse(artifacts.analyticsSpec)
                        : artifacts.analyticsSpec
                      return JSON.stringify(parsed, null, 2)
                    } catch {
                      return artifacts.analyticsSpec
                    }
                  })()}
                </pre>
              </div>
            </TabsContent>
          )}

          {summary && (
            <TabsContent value="summary" className="mt-0 p-4">
              <RunSummaryCard summary={summary} failureMessage={failureMessage} />
            </TabsContent>
          )}
        </ScrollArea>
      </Tabs>
    </div>
  )
}
