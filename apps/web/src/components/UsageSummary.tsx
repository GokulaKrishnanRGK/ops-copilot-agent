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

export function UsageSummary({
  sessionMetrics,
  latestRun,
  loading,
  onOpenDetails,
}: UsageSummaryProps) {
  const latestRunMetrics = latestRun?.metrics ?? null;

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
