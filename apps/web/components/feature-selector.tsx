"use client"

import type { FeatureChoice } from "@/lib/types"

interface FeatureSelectorProps {
  features: FeatureChoice[]
  onSelect: (index: number) => void
}

export function FeatureSelector({ features, onSelect }: FeatureSelectorProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-lg rounded-lg border border-border bg-card shadow-2xl">
        <div className="border-b border-border px-6 py-4">
          <h2 className="text-base font-semibold text-foreground">Select a Feature</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Choose the highest-impact feature to implement. Each is ranked by evidence frequency, severity, and effort.
          </p>
        </div>
        <div className="space-y-3 p-6">
          {features.map((feature, i) => (
            <button
              key={feature.feature}
              type="button"
              onClick={() => onSelect(i)}
              className="group w-full rounded-lg border border-border bg-secondary/30 p-4 text-left transition-all hover:border-primary/50 hover:bg-primary/5 focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-secondary text-[10px] font-bold text-muted-foreground group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                      {i + 1}
                    </span>
                    <span className="text-sm font-semibold text-foreground">{feature.feature}</span>
                  </div>
                  <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed pl-7">
                    {feature.rationale}
                  </p>
                  <div className="mt-2 flex gap-1 pl-7">
                    {feature.linked_claim_ids.map((id) => (
                      <span key={id} className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] text-primary">
                        {id}
                      </span>
                    ))}
                  </div>
                </div>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="mt-1 shrink-0 text-muted-foreground/30 group-hover:text-primary transition-colors"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </div>
            </button>
          ))}
        </div>
        <div className="border-t border-border px-6 py-3">
          <div className="flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted-foreground">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <span className="text-[10px] text-muted-foreground">
              Option 1 is recommended based on evidence ranking. Click to select.
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
