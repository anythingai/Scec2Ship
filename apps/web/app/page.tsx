"use client"

import { AppHeader } from "@/components/app-header"
import { InputPanel } from "@/components/input-panel"
import { TimelinePanel } from "@/components/timeline-panel"
import { ArtifactsPanel } from "@/components/artifacts-panel"
import { FeatureSelector } from "@/components/feature-selector"
import { useRunStore } from "@/lib/use-run-store"
import { useState } from "react"

export default function Page() {
  const {
    state,
    startRun,
    cancelRun,
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
    loadRunHistory,
    replayRun,
  } = useRunStore()

  const [mobileTab, setMobileTab] = useState<"input" | "pipeline" | "artifacts">("input")

  return (
    <div className="flex h-screen flex-col bg-background">
      <AppHeader status={state.status} runId={state.runId} onReset={resetRun} />

      {/* Mobile Tab Bar */}
      <div className="flex border-b border-border lg:hidden">
        <button
          type="button"
          onClick={() => setMobileTab("input")}
          className={`flex-1 py-2 text-center text-xs font-medium transition-colors ${
            mobileTab === "input" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"
          }`}
        >
          Input
        </button>
        <button
          type="button"
          onClick={() => setMobileTab("pipeline")}
          className={`flex-1 py-2 text-center text-xs font-medium transition-colors ${
            mobileTab === "pipeline" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"
          }`}
        >
          Pipeline
        </button>
        <button
          type="button"
          onClick={() => setMobileTab("artifacts")}
          className={`flex-1 py-2 text-center text-xs font-medium transition-colors ${
            mobileTab === "artifacts" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"
          }`}
        >
          Artifacts
        </button>
      </div>

      {/* Desktop: 3-panel layout */}
      <div className="hidden lg:flex flex-1 overflow-hidden">
        <div className="w-72 shrink-0">
          <InputPanel
            workspace={state.workspace}
            evidenceFiles={state.evidenceFiles}
            status={state.status}
            gitHub={state.gitHub}
            useSample={state.useSample}
            fastMode={state.fastMode}
            onUpdateWorkspace={updateWorkspace}
            onUpdateGuardrails={updateGuardrails}
            onSetEvidenceFiles={setEvidenceFiles}
            onSetUseSample={setUseSample}
            onSetFastMode={setFastMode}
            onLoadSample={loadSampleEvidence}
            onStartRun={startRun}
            onCancelRun={cancelRun}
            onConnectGitHub={connectGitHub}
            onDisconnectGitHub={disconnectGitHub}
            onLoadRunHistory={() => loadRunHistory(state.workspaceId)}
            onReplayRun={replayRun}
          />
        </div>
        <div className="w-80 shrink-0">
          <TimelinePanel
            stages={state.stages}
            logs={state.logs}
            status={state.status}
            retryCount={state.retryCount}
          />
        </div>
        <div className="flex-1 min-w-0">
          <ArtifactsPanel
            artifacts={state.artifacts}
            status={state.status}
            isPrMode={state.workspace.guardrails.mode === "pr"}
            showCitations={state.showCitations}
            onToggleCitations={toggleCitations}
            summary={state.summary}
            failureMessage={state.failureMessage}
            runId={state.runId}
          />
        </div>
      </div>

      {/* Mobile: single panel */}
      <div className="flex flex-1 overflow-hidden lg:hidden">
        {mobileTab === "input" && (
          <div className="w-full">
            <InputPanel
              workspace={state.workspace}
              evidenceFiles={state.evidenceFiles}
              status={state.status}
              gitHub={state.gitHub}
              useSample={state.useSample}
              fastMode={state.fastMode}
              onUpdateWorkspace={updateWorkspace}
              onUpdateGuardrails={updateGuardrails}
              onSetEvidenceFiles={setEvidenceFiles}
              onSetUseSample={setUseSample}
              onSetFastMode={setFastMode}
              onLoadSample={loadSampleEvidence}
              onStartRun={startRun}
              onCancelRun={cancelRun}
              onConnectGitHub={connectGitHub}
              onDisconnectGitHub={disconnectGitHub}
              onLoadRunHistory={() => loadRunHistory(state.workspaceId)}
              onReplayRun={replayRun}
            />
          </div>
        )}
        {mobileTab === "pipeline" && (
          <div className="w-full">
            <TimelinePanel
              stages={state.stages}
              logs={state.logs}
              status={state.status}
              retryCount={state.retryCount}
            />
          </div>
        )}
        {mobileTab === "artifacts" && (
          <div className="w-full">
            <ArtifactsPanel
              artifacts={state.artifacts}
              status={state.status}
              isPrMode={state.workspace.guardrails.mode === "pr"}
              showCitations={state.showCitations}
              onToggleCitations={toggleCitations}
              summary={state.summary}
              failureMessage={state.failureMessage}
              runId={state.runId}
            />
          </div>
        )}
      </div>

      {/* Feature Selection Modal */}
      {state.showFeatureSelection && state.topFeatures.length > 0 && (
        <FeatureSelector features={state.topFeatures} onSelect={selectFeature} />
      )}
    </div>
  )
}
