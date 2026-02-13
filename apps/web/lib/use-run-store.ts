"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { toast } from "sonner";
import type {
  RunState,
  Stage,
  LogEntry,
  EvidenceFile,
  RunSummary as RunSummaryData,
  Workspace,
} from "./types";
import { PIPELINE_STAGES } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (typeof window !== "undefined" ? window.location.origin : "");

type ArtifactKey = keyof RunState["artifacts"];
type EvidenceMapData = NonNullable<RunState["artifacts"]["evidenceMap"]>;

const STAGE_TO_ARTIFACT: Record<
  string,
  { file: string; key: ArtifactKey; type: "text" | "json" }
> = {
  SYNTHESIZE: { file: "evidence-map.json", key: "evidenceMap", type: "json" },
  GENERATE_PRD: { file: "PRD.md", key: "prd", type: "text" },
  GENERATE_DESIGN: { file: "wireframes.html", key: "wireframes", type: "text" },
  GENERATE_TICKETS: { file: "tickets.json", key: "tickets", type: "json" },
  IMPLEMENT: { file: "diff.patch", key: "diff", type: "text" },
  VERIFY: { file: "test-report.md", key: "testReport", type: "text" },
  EXPORT: { file: "audit-trail.json", key: "auditTrail", type: "json" },
};

const inferEvidenceType = (name: string): EvidenceFile["type"] => {
  const lower = name.toLowerCase();
  if (lower.includes("support_tickets")) return "support_tickets";
  if (lower.includes("usage_metrics")) return "usage_metrics";
  if (lower.includes("competitors")) return "competitors";
  if (lower.includes("nps")) return "nps_comments";
  if (lower.includes("changelog")) return "changelog";
  return "interview";
};

function initialState(): RunState {
  return {
    runId: null,
    status: "idle",
    stages: PIPELINE_STAGES.map((stage) => ({
      ...stage,
      status: "pending" as const,
    })),
    logs: [],
    retryCount: 0,
    artifacts: {
      prd: null,
      wireframes: null,
      userFlow: null,
      tickets: null,
      ticketsEpicTitle: null,
      evidenceMap: null,
      diff: null,
      testReport: null,
      auditTrail: null,
      deviationAlert: null,
      decisionMemo: null,
      goToMarket: null,
      analyticsSpec: null,
    },
    workspace: {
      teamName: "",
      repoUrl: "",
      branch: "main",
      goalStatement: "",
      guardrails: {
        maxRetries: 2,
        mode: "read_only",
        forbiddenPaths: [],
      },
      okrConfig: null,
      approvalWorkflowEnabled: false,
    },
    evidenceFiles: [],
    useSample: false,
    fastMode: true,
    selectedFeatureIndex: null,
    topFeatures: [],
    showFeatureSelection: false,
    designSystemTokens: "",
    summary: null,
    showCitations: false,
    failureMessage: null,
    gitHub: { connected: false, username: undefined, token: undefined },
    workspaceId: null,
  };
}

export function useRunStore() {
  const [state, setState] = useState<RunState>(initialState());
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const setStageStatus = useCallback(
    (stageId: string, updates: Partial<Stage>) => {
      setState((prev) => ({
        ...prev,
        stages: prev.stages.map((stage) =>
          stage.id === stageId ? { ...stage, ...updates } : stage,
        ),
      }));
    },
    [],
  );

  const addLog = useCallback((log: LogEntry) => {
    setState((prev) => ({ ...prev, logs: [...prev.logs, log] }));
  }, []);

  const setArtifacts = useCallback(
    (updates: Partial<RunState["artifacts"]>) => {
      setState((prev) => {
        const next = { ...prev, artifacts: { ...prev.artifacts, ...updates } };
        if (
          updates.evidenceMap &&
          Array.isArray(updates.evidenceMap.topFeatures)
        ) {
          next.topFeatures = updates.evidenceMap.topFeatures;
        }
        return next;
      });
    },
    [],
  );

  const normalizeEvidenceMap = useCallback(
    (raw: unknown): RunState["artifacts"]["evidenceMap"] => {
      if (!raw || typeof raw !== "object") return null;
      const payload = raw as Record<string, unknown>;
      const topFeatures =
        (Array.isArray(payload.topFeatures) && payload.topFeatures) ||
        (Array.isArray(payload.top_features) && payload.top_features) ||
        [];
      const featureChoice =
        (payload.featureChoice as EvidenceMapData["featureChoice"]) ||
        (payload.feature_choice as EvidenceMapData["featureChoice"]) ||
        null;
      return {
        summary:
          typeof payload.summary === "string" ? payload.summary : undefined,
        claims: Array.isArray(payload.claims)
          ? (payload.claims as EvidenceMapData["claims"])
          : [],
        featureChoice,
        topFeatures: topFeatures as EvidenceMapData["topFeatures"],
      };
    },
    [],
  );

  const normalizeTickets = useCallback(
    (
      raw: unknown,
    ): {
      tickets: RunState["artifacts"]["tickets"];
      epicTitle: string | null;
    } => {
      if (!raw) return { tickets: null, epicTitle: null };
      if (Array.isArray(raw))
        return {
          tickets: raw as RunState["artifacts"]["tickets"],
          epicTitle: null,
        };
      if (typeof raw !== "object") return { tickets: null, epicTitle: null };
      const payload = raw as Record<string, unknown>;
      const tickets = Array.isArray(payload.tickets)
        ? (payload.tickets as RunState["artifacts"]["tickets"])
        : null;
      const epicTitle =
        typeof payload.epic_title === "string" ? payload.epic_title : null;
      return { tickets, epicTitle };
    },
    [],
  );

  const setEvidenceFiles = useCallback((files: EvidenceFile[]) => {
    setState((prev) => ({ ...prev, evidenceFiles: files }));
  }, []);

  const updateWorkspace = useCallback((updates: Partial<Workspace>) => {
    setState((prev) => ({
      ...prev,
      workspace: { ...prev.workspace, ...updates },
    }));
  }, []);

  const updateGuardrails = useCallback(
    (updates: Partial<Workspace["guardrails"]>) => {
      setState((prev) => ({
        ...prev,
        workspace: {
          ...prev.workspace,
          guardrails: { ...prev.workspace.guardrails, ...updates },
        },
      }));
    },
    [],
  );

  const loadSampleEvidence = useCallback(async () => {
    if (!API_BASE) return;
    try {
      const res = await fetch(`${API_BASE}/sample/evidence`);
      if (!res.ok) return;
      const data = await res.json();
      const files = (data.files as string[]) ?? [];
      const interviews = (data.interviews as string[]) ?? [];
      const combined = [
        ...files,
        ...interviews.map((name) => `interviews/${name}`),
      ];
      setEvidenceFiles(
        combined.map((name) => ({
          name,
          type: inferEvidenceType(name),
          size: 0,
          status: "valid",
        })),
      );
      setState((prev) => ({ ...prev, useSample: true }));
      updateWorkspace({
        teamName: "Acme Corp",
        repoUrl: "local://target-repo",
        branch: "main",
        goalStatement: "Improve onboarding completion rate from 23% to 70%",
      });
      updateGuardrails({ forbiddenPaths: ["/infra", "/payments"] });
    } catch (error) {
      console.error("Failed to load sample evidence", error);
    }
  }, [setEvidenceFiles, updateWorkspace, updateGuardrails]);

  const resetRun = useCallback(() => {
    eventSourceRef.current?.close();
    setState(initialState());
  }, []);

  const fetchArtifactText = useCallback(async (runId: string, name: string) => {
    const res = await fetch(`${API_BASE}/runs/${runId}/artifacts/${name}`);
    if (!res.ok) return null;
    return res.text();
  }, []);

  const fetchRunSummary = useCallback(async (runId: string) => {
    const res = await fetch(`${API_BASE}/runs/${runId}`);
    if (!res.ok) return null;
    return (await res.json()) as {
      retry_count: number;
      summary: RunSummaryData | null;
    };
  }, []);

  const refreshArtifacts = useCallback(
    async (runId: string) => {
      const res = await fetch(`${API_BASE}/runs/${runId}/artifacts`);
      if (!res.ok) return;
      const payload = await res.json();
      const updates: Partial<RunState["artifacts"]> = {};
      if (payload.artifacts.includes("PRD.md")) {
        updates.prd = await fetchArtifactText(runId, "PRD.md");
      }
      if (payload.artifacts.includes("tickets.json")) {
        const text = await fetchArtifactText(runId, "tickets.json");
        if (text) {
          try {
            const parsed = JSON.parse(text);
            const { tickets, epicTitle } = normalizeTickets(parsed);
            updates.tickets = tickets;
            updates.ticketsEpicTitle = epicTitle;
          } catch (error) {
            console.error("tickets parse", error);
          }
        }
      }
      if (payload.artifacts.includes("evidence-map.json")) {
        const text = await fetchArtifactText(runId, "evidence-map.json");
        if (text) {
          try {
            const parsed = JSON.parse(text);
            updates.evidenceMap = normalizeEvidenceMap(parsed);
          } catch (error) {
            console.error("evidence map parse", error);
          }
        }
      }
      if (payload.artifacts.includes("diff.patch")) {
        updates.diff = await fetchArtifactText(runId, "diff.patch");
      }
      if (payload.artifacts.includes("test-report.md")) {
        updates.testReport = await fetchArtifactText(runId, "test-report.md");
      }
      if (payload.artifacts.includes("wireframes.html")) {
        updates.wireframes = await fetchArtifactText(runId, "wireframes.html");
      }
      if (payload.artifacts.includes("user-flow.mmd")) {
        updates.userFlow = await fetchArtifactText(runId, "user-flow.mmd");
      }
      if (payload.artifacts.includes("audit-trail.json")) {
        const text = await fetchArtifactText(runId, "audit-trail.json");
        if (text) {
          try {
            updates.auditTrail = JSON.parse(text);
          } catch {
            // ignore
          }
        }
      }
      if (payload.artifacts.includes("deviation-alert.json")) {
        const text = await fetchArtifactText(runId, "deviation-alert.json");
        if (text) {
          try {
            const parsed = JSON.parse(text);
            updates.deviationAlert = parsed.run_id ? parsed : null;
          } catch {
            updates.deviationAlert = null;
          }
        } else {
          updates.deviationAlert = null;
        }
      } else {
        updates.deviationAlert = null;
      }
      if (payload.artifacts.includes("decision-memo.md")) {
        updates.decisionMemo = await fetchArtifactText(runId, "decision-memo.md");
      } else {
        updates.decisionMemo = null;
      }
      if (payload.artifacts.includes("go-to-market.md")) {
        updates.goToMarket = await fetchArtifactText(runId, "go-to-market.md");
      } else {
        updates.goToMarket = null;
      }
      if (payload.artifacts.includes("analytics-spec.json")) {
        updates.analyticsSpec = await fetchArtifactText(runId, "analytics-spec.json");
      } else {
        updates.analyticsSpec = null;
      }
      setArtifacts(updates);
    },
    [fetchArtifactText, normalizeEvidenceMap, normalizeTickets, setArtifacts],
  );

  const loadArtifactForStage = useCallback(
    async (runId: string, stageId: string) => {
      const descriptor = STAGE_TO_ARTIFACT[stageId];
      if (!descriptor) return;
      const text = await fetchArtifactText(runId, descriptor.file);
      if (!text) return;
      if (descriptor.type === "json") {
        try {
          if (descriptor.file === "audit-trail.json") {
            const parsed = JSON.parse(text);
            setArtifacts({ auditTrail: parsed } as Partial<RunState["artifacts"]>);
            return;
          }
          if (descriptor.file === "tickets.json") {
            const parsed = JSON.parse(text);
            const { tickets, epicTitle } = normalizeTickets(parsed);
            setArtifacts({
              [descriptor.key]: tickets,
              ticketsEpicTitle: epicTitle,
            } as Partial<RunState["artifacts"]>);
            return;
          }
          if (descriptor.file === "evidence-map.json") {
            const parsed = JSON.parse(text);
            setArtifacts({
              [descriptor.key]: normalizeEvidenceMap(parsed),
            } as Partial<RunState["artifacts"]>);
            return;
          }
          setArtifacts({ [descriptor.key]: JSON.parse(text) } as Partial<
            RunState["artifacts"]
          >);
        } catch (error) {
          console.error("artifact parse", error);
        }
        return;
      }
      setArtifacts({ [descriptor.key]: text } as Partial<
        RunState["artifacts"]
      >);
    },
    [fetchArtifactText, normalizeEvidenceMap, normalizeTickets, setArtifacts],
  );

  const handleRunComplete = useCallback(
    async (runId: string, outcome: RunState["status"], error?: string) => {
      const summary = await fetchRunSummary(runId);
      setState((prev) => ({
        ...prev,
        status: outcome,
        failureMessage: error ?? (outcome === "failed" ? "Run failed" : null),
        retryCount: summary?.retry_count ?? prev.retryCount,
        summary: summary?.summary ?? prev.summary,
      }));
      await refreshArtifacts(runId);
    },
    [fetchRunSummary, refreshArtifacts],
  );

  const subscribeToRun = useCallback(
    (runId: string) => {
      eventSourceRef.current?.close();
      if (!API_BASE) return;
      const source = new EventSource(`${API_BASE}/runs/${runId}/events`);
      eventSourceRef.current = source;
      source.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        addLog({
          timestamp: payload.timestamp,
          stage: payload.stage ?? "RUN",
          message: payload.error
            ? `ERROR · ${payload.error}`
            : `${payload.stage ?? "RUN"}: ${payload.action} → ${payload.outcome}`,
          level: payload.error ? "error" : "info",
        });
        if (payload.stage && payload.action === "stage_start") {
          setStageStatus(payload.stage, {
            status: "running",
            startedAt: payload.timestamp,
          });
        }
        if (payload.stage && payload.action === "stage_end") {
          const status = payload.outcome === "done" ? "done" : "failed";
          setStageStatus(payload.stage, {
            status,
            completedAt: payload.timestamp,
            error: payload.error || undefined,
          });
          void loadArtifactForStage(runId, payload.stage);
          if (payload.stage === "GENERATE_DESIGN" && status === "done") {
            fetchArtifactText(runId, "user-flow.mmd").then((text) => {
              if (text) setArtifacts({ userFlow: text });
            });
          }
        }
        if (payload.action === "feature_selection_required") {
          setState((prev) => ({
            ...prev,
            showFeatureSelection: true,
          }));
        }
        if (payload.action === "feature_selected") {
          setState((prev) => ({
            ...prev,
            selectedFeatureIndex:
              Number(payload.outcome) || prev.selectedFeatureIndex,
            showFeatureSelection: false,
          }));
        }
        if (payload.stage === "AWAITING_APPROVAL" && payload.action === "approval_requested") {
          setState((prev) => ({ ...prev, status: "awaiting_approval" }));
          setStageStatus("AWAITING_APPROVAL", {
            status: "running",
            startedAt: payload.timestamp,
          });
          toast.info("PRD & design ready for review", {
            description: "Approve or request changes in the Artifacts panel to continue.",
          });
        }
        if (
          payload.action === "run_completed" ||
          payload.action === "run_failed"
        ) {
          const outcome: RunState["status"] =
            payload.outcome === "completed" ? "completed" : "failed";
          void handleRunComplete(runId, outcome, payload.error);
          source.close();
        }
      };
      source.onerror = () => source.close();
    },
    [addLog, fetchArtifactText, handleRunComplete, loadArtifactForStage, setArtifacts, setStageStatus],
  );

  const startRun = useCallback(async () => {
    const workspacePayload = {
      team_name: state.workspace.teamName,
      repo_url: state.workspace.repoUrl || "local://target-repo",
      branch: state.workspace.branch,
      guardrails: {
        max_retries: state.workspace.guardrails.maxRetries,
        mode: state.workspace.guardrails.mode,
        forbidden_paths: state.workspace.guardrails.forbiddenPaths,
      },
      okr_config: state.workspace.okrConfig
        ? {
            okrs: state.workspace.okrConfig.okrs,
            north_star_metric: state.workspace.okrConfig.northStarMetric ?? null,
          }
        : null,
      approval_workflow_enabled: state.workspace.approvalWorkflowEnabled ?? false,
      approvers: state.workspace.approvers ?? [],
      linear_url: state.workspace.linearUrl ?? null,
      jira_url: state.workspace.jiraUrl ?? null,
    };
    const workspaceRes = await fetch(`${API_BASE}/workspaces`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(workspacePayload),
    });
    if (!workspaceRes.ok) {
      setState((prev) => ({
        ...prev,
        failureMessage: "Unable to create workspace",
      }));
      return;
    }
    const workspaceData = await workspaceRes.json();

    // If GitHub is connected in UI state, sync it to the backend workspace
    if (state.gitHub.connected && state.gitHub.token) {
      await fetch(`${API_BASE}/auth/github`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: workspaceData.workspace_id,
          github_token: state.gitHub.token,
        }),
      });
    }

    const runForm = new FormData();
    runForm.append("workspace_id", workspaceData.workspace_id);
    runForm.append("use_sample", String(state.useSample));
    runForm.append("fast_mode", String(state.fastMode));
    if (state.workspace.goalStatement)
      runForm.append("goal_statement", state.workspace.goalStatement);
    if (state.selectedFeatureIndex !== null)
      runForm.append(
        "selected_feature_index",
        String(state.selectedFeatureIndex),
      );
    if (state.designSystemTokens)
      runForm.append("design_system_tokens", state.designSystemTokens);
    if (!state.useSample) {
      state.evidenceFiles.forEach((file) => {
        if (file.file) runForm.append("files", file.file);
      });
    }
    const runRes = await fetch(`${API_BASE}/runs`, {
      method: "POST",
      body: runForm,
    });
    if (!runRes.ok) {
      setState((prev) => ({ ...prev, failureMessage: "Unable to start run" }));
      return;
    }
    const run = await runRes.json();
    setState((prev) => ({
      ...prev,
      workspaceId: workspaceData.workspace_id,
      runId: run.run_id,
      status: "running",
      logs: [],
      stages: PIPELINE_STAGES.map((stage) => ({
        ...stage,
        status: "pending" as const,
      })),
      artifacts: {
        prd: null,
        wireframes: null,
        userFlow: null,
        tickets: null,
        ticketsEpicTitle: null,
        evidenceMap: null,
        diff: null,
        testReport: null,
        auditTrail: null,
        deviationAlert: null,
        decisionMemo: null,
        goToMarket: null,
        analyticsSpec: null,
      },
      failureMessage: null,
    }));
    subscribeToRun(run.run_id);
  }, [
    state.workspace,
    state.useSample,
    state.fastMode,
    state.selectedFeatureIndex,
    state.evidenceFiles,
    state.designSystemTokens,
    state.gitHub.connected,
    state.gitHub.token,
    subscribeToRun,
  ]);

  const cancelRun = useCallback(async () => {
    if (!state.runId) return;
    await fetch(`${API_BASE}/runs/${state.runId}/cancel`, { method: "POST" });
    setState((prev) => ({ ...prev, status: "cancelled" }));
  }, [state.runId]);

  const approveRun = useCallback(
    async (approved: boolean) => {
      if (!state.runId) return;
      await fetch(`${API_BASE}/runs/${state.runId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
      if (approved) {
        setState((prev) => ({ ...prev, status: "running" }));
      } else {
        setState((prev) => ({ ...prev, status: "failed", failureMessage: "Changes requested" }));
      }
    },
    [state.runId],
  );

  const setDesignSystemTokens = useCallback((value: string) => {
    setState((prev) => ({ ...prev, designSystemTokens: value }));
  }, []);

  const selectFeature = useCallback(
    async (index: number) => {
      if (!state.runId) return;
      await fetch(`${API_BASE}/runs/${state.runId}/select-feature`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selected_feature_index: index }),
      });
      setState((prev) => ({
        ...prev,
        selectedFeatureIndex: index,
        showFeatureSelection: false,
      }));
    },
    [state.runId],
  );

  const toggleCitations = useCallback(() => {
    setState((prev) => ({ ...prev, showCitations: !prev.showCitations }));
  }, []);

  const connectGitHub = useCallback((token: string, username: string) => {
    setState((prev) => ({
      ...prev,
      gitHub: { connected: true, token, username },
    }));
  }, []);

  const disconnectGitHub = useCallback(() => {
    setState((prev) => ({
      ...prev,
      gitHub: { connected: false, token: undefined, username: undefined },
    }));
  }, []);

  const loadRunHistory = useCallback(async (workspaceId: string | null) => {
    if (!workspaceId || !API_BASE) return [];
    try {
      const url = workspaceId ? `${API_BASE}/runs?workspace_id=${workspaceId}` : `${API_BASE}/runs`;
      const res = await fetch(url);
      if (!res.ok) return [];
      const data = await res.json();
      return (data.runs || []).filter((r: { status: string }) => 
        r.status === "completed" || r.status === "failed"
      );
    } catch {
      return [];
    }
  }, []);

  const replayRun = useCallback(async (runId: string) => {
    if (!API_BASE) return;
    try {
      const res = await fetch(`${API_BASE}/runs/${runId}/replay`);
      if (!res.ok) throw new Error("Failed to load run");
      const summary = await res.json();
      
      // Reset state and load run
      setState((prev) => ({
        ...prev,
        runId: summary.run_id,
        status: summary.status as RunState["status"],
        retryCount: summary.retry_count,
        stages: PIPELINE_STAGES.map((stage) => {
          // Infer stage status from summary
          let status: Stage["status"] = "pending";
          if (summary.status === "completed") {
            status = "done";
          } else if (summary.status === "failed") {
            status = stage.id === "VERIFY" ? "failed" : "done";
          }
          return { ...stage, status };
        }),
        logs: [],
        artifacts: {
          prd: null,
          wireframes: null,
          userFlow: null,
          tickets: null,
          ticketsEpicTitle: null,
          evidenceMap: null,
          diff: null,
          testReport: null,
          auditTrail: null,
          deviationAlert: null,
          decisionMemo: null,
          goToMarket: null,
          analyticsSpec: null,
        },
      }));
      
      // Load artifacts and logs
      await handleRunComplete(runId, summary.status as RunState["status"], undefined);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        failureMessage: `Failed to replay run: ${err instanceof Error ? err.message : "Unknown error"}`,
      }));
    }
  }, [handleRunComplete]);

  const setUseSample = useCallback((value: boolean) => {
    setState((prev) => ({ ...prev, useSample: value }));
  }, []);

  const setFastMode = useCallback((value: boolean) => {
    setState((prev) => ({ ...prev, fastMode: value }));
  }, []);

  return {
    state,
    startRun,
    cancelRun,
    approveRun,
    resetRun,
    loadSampleEvidence,
    setEvidenceFiles,
    updateWorkspace,
    updateGuardrails,
    selectFeature,
    toggleCitations,
    connectGitHub,
    disconnectGitHub,
    setUseSample,
    setFastMode,
    setDesignSystemTokens,
    loadRunHistory,
    replayRun,
    refreshArtifacts,
  };
}
