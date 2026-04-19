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

export function UsageSummary({
  sessionMetrics,
  latestRun,
  loading,
  onOpenDetails,
}: UsageSummaryProps) {
  const latestRunMetrics = latestRun?.metrics ?? null;
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
      <div className="cost-status-row" title="Latest run estimated cost">
        <span className="cost-status-item">
          <span className="usage-group-label">Estimated cost</span>
          <strong>{formatCost(latestRunMetrics?.usage.cost_usd ?? 0)}</strong>
        </span>
      </div>
      <div className="usage-row">
        <div className="usage-group" title="Aggregated usage for this session">
          <span className="usage-group-label">Session</span>
          <span className="usage-chip">
            Est. cost {formatCost(sessionMetrics?.usage.cost_usd ?? 0)}
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
            Est. cost {formatCost(latestRunMetrics?.usage.cost_usd ?? 0)}
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
