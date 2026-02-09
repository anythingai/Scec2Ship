export type StageStatus = "pending" | "running" | "done" | "failed" | "retry" | "skipped"

export type RunStatus = "idle" | "pending" | "running" | "retrying" | "completed" | "failed" | "cancelled"

export interface Stage {
  id: string
  label: string
  description: string
  status: StageStatus
  startedAt?: string
  completedAt?: string
  error?: string
  retryIndex?: number
}

export interface LogEntry {
  timestamp: string
  stage: string
  message: string
  level: "info" | "warn" | "error" | "success"
}

export interface EvidenceFile {
  name: string
  type: "interview" | "support_tickets" | "usage_metrics" | "competitors" | "nps_comments" | "changelog"
  size: number
  status: "valid" | "invalid" | "pending"
  error?: string
  file?: File
}

export interface Guardrails {
  maxRetries: number
  mode: "read_only" | "pr"
  forbiddenPaths: string[]
}

export interface Workspace {
  teamName: string
  repoUrl: string
  branch: string
  goalStatement: string
  guardrails: Guardrails
  workspaceId?: string | null
}

export interface GitHubConnection {
  connected: boolean
  username?: string
  token?: string
}

export interface Ticket {
  id: string
  title: string
  description: string
  acceptance_criteria: string[]
  files_expected: string[]
  risk_level: "low" | "med" | "high"
  estimate_hours: number
  owner: string | null
}

export interface Claim {
  claim_id: string
  claim_text: string
  supporting_sources: {
    file: string
    line_range: [number, number]
    quote: string
  }[]
  confidence: number
}

export interface FeatureChoice {
  feature: string
  rationale: string
  linked_claim_ids: string[]
}

export interface EvidenceMap {
  summary?: string
  claims: Claim[]
  featureChoice: FeatureChoice | null
  topFeatures: FeatureChoice[]
}

export interface RunSummary {
  passFail: "pass" | "fail"
  retriesUsed: number
  filesChanged: string[]
  confidenceScore: number
  totalTickets: number
  totalEstimateHours: number
  testsPassed: number
  testsFailed: number
  testsSkipped: number
  duration: string
  prUrl?: string | null
}

export interface RunHistoryItem {
  run_id: string
  workspace_id: string
  status: string
  current_stage: string | null
  retry_count: number
  outputs_index: Record<string, string | null>
  summary: Record<string, unknown> | null
  created_at: string | null
  completed_at: string | null
}

export interface RunState {
  runId: string | null
  status: RunStatus
  stages: Stage[]
  logs: LogEntry[]
  retryCount: number
  artifacts: {
    prd: string | null
    tickets: Ticket[] | null
    ticketsEpicTitle: string | null
    evidenceMap: EvidenceMap | null
    diff: string | null
    testReport: string | null
  }
  workspace: Workspace
  evidenceFiles: EvidenceFile[]
  useSample: boolean
  fastMode: boolean
  selectedFeatureIndex: number | null
  topFeatures: FeatureChoice[]
  showFeatureSelection: boolean
  summary: RunSummary | null
  showCitations: boolean
  failureMessage: string | null
  gitHub: GitHubConnection
  workspaceId: string | null
}

export const PIPELINE_STAGES: Omit<Stage, "status">[] = [
  { id: "INTAKE", label: "Intake", description: "Validate evidence & detect stack" },
  { id: "SYNTHESIZE", label: "Synthesize", description: "Cluster evidence & rank themes" },
  { id: "SELECT_FEATURE", label: "Select Feature", description: "Choose highest-impact feature" },
  { id: "GENERATE_PRD", label: "Generate PRD", description: "Produce PRD with acceptance criteria" },
  { id: "GENERATE_TICKETS", label: "Generate Tickets", description: "Create structured tickets" },
  { id: "IMPLEMENT", label: "Implement", description: "Generate code patch" },
  { id: "VERIFY", label: "Verify", description: "Run tests & lint checks" },
  { id: "SELF_HEAL", label: "Self-Heal", description: "Auto-fix on failure" },
  { id: "EXPORT", label: "Export", description: "Package artifact bundle" },
]
