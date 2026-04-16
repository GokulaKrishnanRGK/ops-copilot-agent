import { useMemo } from "react";
import { Run, SessionMetrics } from "../types";

type UsageSummaryProps = {
  sessionMetrics: SessionMetrics | null;
  latestRun: Run | null;
  loading: boolean;
  onOpenDetails: () => void;
};

function formatCost(value: number): string {
  return `$${value.toFixed(4)}`;
}

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function compactModelId(modelId: string): string {
  if (!modelId.trim()) {
    return "unknown";
  }
  const parts = modelId.split(".");
  return parts[parts.length - 1] || modelId;
}

function formatBudgetStatus(status: string): string {
  if (!status.trim()) {
    return "Unknown";
  }
  return status.replaceAll("_", " ");
}

function budgetPercent(totalUsd: number, maxUsd: number | null): number {
  if (maxUsd === null || maxUsd <= 0) {
    return 0;
  }
  return Math.min(100, Math.max(0, (totalUsd / maxUsd) * 100));
}

export function UsageSummary({
  sessionMetrics,
  latestRun,
  loading,
  onOpenDetails,
}: UsageSummaryProps) {
  const latestRunMetrics = latestRun?.metrics ?? null;
  const latestBudget = latestRunMetrics?.budget ?? null;
  const latestBudgetMax = latestBudget?.max_usd ?? null;
  const latestBudgetTotal = latestBudget?.total_usd ?? 0;
  const latestBudgetRemaining = latestBudget?.remaining_usd ?? null;
  const latestBudgetPercent = budgetPercent(latestBudgetTotal, latestBudgetMax);
  const primaryModel = latestRunMetrics?.model_usage[0] ?? null;

  const hasAnyMetrics = useMemo(() => {
    if (sessionMetrics && sessionMetrics.run_count > 0) {
      return true;
    }
    return latestRunMetrics !== null;
  }, [sessionMetrics, latestRunMetrics]);

  if (!hasAnyMetrics && !loading) {
    return null;
  }

  return (
    <div className="usage-summary">
      <div className="budget-surface" title="Latest run budget">
        <div className="budget-surface-main">
          <span className="usage-group-label">Run budget</span>
          <strong>{formatBudgetStatus(latestBudget?.status ?? "unknown")}</strong>
          {primaryModel ? (
            <span title={primaryModel.model_id}>
              {primaryModel.provider} / {compactModelId(primaryModel.model_id)}
            </span>
          ) : null}
          <span>{formatCost(latestBudgetTotal)} spent</span>
          <span>
            {latestBudgetRemaining === null
              ? "No limit"
              : `${formatCost(latestBudgetRemaining)} remaining`}
          </span>
        </div>
        <div className="budget-meter" aria-label="Latest run budget usage">
          <span style={{ width: `${latestBudgetPercent}%` }} />
        </div>
      </div>
      <div className="usage-row">
        <div className="usage-group" title="Aggregated usage for this session">
          <span className="usage-group-label">Session</span>
          <span className="usage-chip">Cost {formatCost(sessionMetrics?.usage.cost_usd ?? 0)}</span>
          <span className="usage-chip">
            Budget {formatCost(sessionMetrics?.budget.total_usd ?? 0)}
          </span>
          <span className="usage-chip">
            In {formatNumber(sessionMetrics?.usage.tokens_input ?? 0)}
          </span>
          <span className="usage-chip">
            Out {formatNumber(sessionMetrics?.usage.tokens_output ?? 0)}
          </span>
          <span className="usage-chip">Runs {formatNumber(sessionMetrics?.run_count ?? 0)}</span>
        </div>
        <div className="usage-group muted" title="Usage for the latest run in this session">
          <span className="usage-group-label">Latest run</span>
          <span className="usage-chip">
            Cost {formatCost(latestRunMetrics?.usage.cost_usd ?? 0)}
          </span>
          <span className="usage-chip">
            Budget {formatCost(latestRunMetrics?.budget.total_usd ?? 0)}
          </span>
          <span className="usage-chip">
            In {formatNumber(latestRunMetrics?.usage.tokens_input ?? 0)}
          </span>
          <span className="usage-chip">
            Out {formatNumber(latestRunMetrics?.usage.tokens_output ?? 0)}
          </span>
          {primaryModel ? (
            <span className="usage-chip" title={primaryModel.model_id}>
              {primaryModel.provider} {compactModelId(primaryModel.model_id)}
            </span>
          ) : null}
        </div>
        <button
          className="button-muted usage-details-toggle"
          type="button"
          onClick={onOpenDetails}
          disabled={!latestRunMetrics}
        >
          Details
        </button>
      </div>
    </div>
  );
}
