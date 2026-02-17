"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface ScorecardMetric {
  label: string
  value: string | number
  threshold?: string | number
  passing?: boolean
}

interface ScorecardData {
  overall_status: "PASS" | "FAIL" | "WARNING"
  evidence_coverage: number
  test_pass_rate: number
  retry_count: number
  max_retries: number
  forbidden_paths_violations: string[]
  summary: string
}

interface ScorecardPanelProps {
  runId: string
  status: string
}

export function ScorecardPanel({ runId, status }: ScorecardPanelProps) {
  const [scorecard, setScorecard] = useState<ScorecardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadScorecard() {
      try {
        const response = await fetch(`/api/runs/${runId}/artifacts`)
        if (response.ok) {
          const data = await response.json()

          // Check if scorecard.json exists in artifacts
          const hasScorecard = data.artifacts?.some((a: string) => a === "scorecard.json")

          if (hasScorecard) {
            // Fetch scorecard content
            const scorecardResponse = await fetch(`/api/runs/${runId}/artifacts/scorecard.json`)
            if (scorecardResponse.ok) {
              const scorecardData = await scorecardResponse.json()
              setScorecard(scorecardData)
            }
          }
        }
      } catch (error) {
        console.error("Failed to load scorecard:", error)
      } finally {
        setLoading(false)
      }
    }

    if (status === "completed" && runId) {
      loadScorecard()
    }
  }, [runId, status])

  if (loading || !scorecard) {
    return (
      <Card className="bg-secondary/30 border-border/50">
        <CardHeader>
          <CardTitle className="text-sm">Verification Scorecard</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            {loading ? "Loading..." : "No scorecard available"}
          </p>
        </CardContent>
      </Card>
    )
  }

  const { overall_status, evidence_coverage, test_pass_rate, retry_count, max_retries, summary } = scorecard

  const statusConfig = {
    PASS: {
      variant: "default" as const,
      className: "bg-success text-success-foreground",
      icon: "✅",
      label: "PASS",
    },
    FAIL: {
      variant: "destructive" as const,
      className: "bg-destructive text-destructive-foreground",
      icon: "❌",
      label: "FAIL",
    },
    WARNING: {
      variant: "outline" as const,
      className: "bg-warning/10 border-warning/50 text-warning",
      icon: "⚠️",
      label: "WARNING",
    },
  }

  const statusInfo = statusConfig[overall_status] || statusConfig.PASS

  const metrics: ScorecardMetric[] = [
    {
      label: "Evidence Coverage",
      value: `${(evidence_coverage * 100).toFixed(0)}%`,
      threshold: "≥ 70%",
      passing: evidence_coverage >= 0.7,
    },
    {
      label: "Test Pass Rate",
      value: `${(test_pass_rate * 100).toFixed(0)}%`,
      threshold: "≥ 80%",
      passing: test_pass_rate >= 0.8,
    },
    {
      label: "Retries Used",
      value: `${retry_count}/${max_retries}`,
      threshold: `≤ ${max_retries}`,
      passing: retry_count <= max_retries,
    },
  ]

  return (
    <div className="space-y-4">
      {/* Overall Status */}
      <Alert className={statusInfo.className}>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{statusInfo.icon}</span>
          <div>
            <AlertDescription className="text-sm font-semibold">
              Verification: {statusInfo.label}
            </AlertDescription>
            <p className="text-xs opacity-90 mt-1">
              {summary}
            </p>
          </div>
        </div>
      </Alert>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        {metrics.map((metric, i) => (
          <Card
            key={i}
            className={`bg-card border ${
              metric.passing === false
                ? "border-destructive/50"
                : "border-border"
            }`}
          >
            <CardContent className="p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                {metric.label}
              </p>
              <p className="text-lg font-bold text-foreground mt-1">
                {typeof metric.value === "number"
                  ? (metric.value as number).toFixed(0)
                  : metric.value}
              </p>
              <p className="text-[10px] text-muted-foreground mt-1">
                Threshold: {metric.threshold}
              </p>
              <div className="mt-2">
                <Badge
                  variant={metric.passing ? "default" : "destructive"}
                  className="text-[9px]"
                >
                  {metric.passing ? "✓ Meets" : "✗ Fails"}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Detailed Metrics */}
      <Card className="bg-secondary/20 border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs text-muted-foreground">
            Detailed Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-start justify-between text-xs">
            <span className="text-muted-foreground">Evidence Coverage</span>
            <span className="font-semibold">
              {(evidence_coverage * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-border rounded-full h-1.5">
            <div
              className={`h-full rounded-full transition-all ${
                evidence_coverage >= 0.7
                  ? "bg-success"
                  : "bg-warning"
              }`}
              style={{ width: `${evidence_coverage * 100}%` }}
            />
          </div>

          <div className="flex items-start justify-between text-xs mt-2">
            <span className="text-muted-foreground">Test Pass Rate</span>
            <span className="font-semibold">
              {(test_pass_rate * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-border rounded-full h-1.5">
            <div
              className={`h-full rounded-full transition-all ${
                test_pass_rate >= 0.8
                  ? "bg-success"
                  : "bg-destructive"
              }`}
              style={{ width: `${test_pass_rate * 100}%` }}
            />
          </div>

          <div className="flex items-center gap-2 text-xs mt-4">
            <span className="text-muted-foreground">Self-Heal Retries:</span>
            <Badge variant="outline" className="font-mono">
              {retry_count}/{max_retries}
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
