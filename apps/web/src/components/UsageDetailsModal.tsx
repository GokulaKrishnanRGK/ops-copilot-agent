import { useEffect, useMemo, useState } from "react";
import { NodeUsage, Run } from "../types";

type UsageDetailsModalProps = {
  isOpen: boolean;
  latestRun: Run | null;
  sessionNodeUsage: NodeUsage[];
  onClose: () => void;
};

function formatCost(value: number): string {
  return `$${value.toFixed(4)}`;
}

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function compactNodeLabel(agentNode: string): string {
  if (!agentNode.trim()) {
    return "unknown";
  }
  return agentNode.replaceAll("_", " ");
}

const PIE_COLORS = [
  "#3ea8ff",
  "#20c997",
  "#ffd166",
  "#ff7f50",
  "#a78bfa",
  "#ff6f91",
  "#4dd0e1",
  "#84cc16",
];

type Slice = {
  key: string;
  label: string;
  value: number;
  tokensInput: number;
  tokensOutput: number;
  costUsd: number;
  color: string;
  midAngle: number;
};

function polarToCartesian(cx: number, cy: number, radius: number, angle: number) {
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

function buildColorMap(items: NodeUsage[]): Map<string, string> {
  const map = new Map<string, string>();
  let index = 0;
  for (const item of items) {
    if (!map.has(item.agent_node)) {
      map.set(item.agent_node, PIE_COLORS[index % PIE_COLORS.length]);
      index += 1;
    }
  }
  return map;
}

function buildPieSlices(items: NodeUsage[], colorMap: Map<string, string>): Slice[] {
  const total = items.reduce((sum, item) => sum + item.tokens_total, 0);
  let cumulativeAngle = -Math.PI / 2;
  return items.map((item) => {
    const value = item.tokens_total;
    const sliceAngle = total > 0 ? (value / total) * Math.PI * 2 : 0;
    const segmentStart = cumulativeAngle;
    cumulativeAngle += sliceAngle;
    return {
      key: item.agent_node,
      label: compactNodeLabel(item.agent_node),
      value,
      tokensInput: item.tokens_input,
      tokensOutput: item.tokens_output,
      costUsd: item.cost_usd,
      color: colorMap.get(item.agent_node) ?? PIE_COLORS[0],
      midAngle: segmentStart + sliceAngle / 2,
    };
  });
}

function PieChart({
  title,
  items,
  colorMap,
}: {
  title: string;
  items: NodeUsage[];
  colorMap: Map<string, string>;
}) {
  const [hoveredKey, setHoveredKey] = useState<string>("");
  const slices = buildPieSlices(items, colorMap);
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);
  const radius = 70;
  const innerRadius = 42;
  const center = 100;

  if (slices.length === 0 || total <= 0) {
    return <p className="usage-details-empty">No records.</p>;
  }

  let cumulativeAngle = -Math.PI / 2;
  return (
    <div className="usage-chart-wrap">
      <svg
        className="usage-pie-chart"
        viewBox="0 0 200 200"
        role="img"
        aria-label={`${title} node usage distribution`}
      >
        {slices.map((slice) => {
          const sliceAngle = (slice.value / total) * Math.PI * 2;
          const segmentStart = cumulativeAngle;
          const start = polarToCartesian(center, center, radius, cumulativeAngle);
          cumulativeAngle += sliceAngle;
          const end = polarToCartesian(center, center, radius, cumulativeAngle);
          const innerEnd = polarToCartesian(center, center, innerRadius, cumulativeAngle);
          const innerStart = polarToCartesian(center, center, innerRadius, segmentStart);
          const largeArc = sliceAngle > Math.PI ? 1 : 0;
          const path = [
            `M ${start.x} ${start.y}`,
            `A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`,
            `L ${innerEnd.x} ${innerEnd.y}`,
            `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${innerStart.x} ${innerStart.y}`,
            "Z",
          ].join(" ");

          return (
            <path
              key={slice.key}
              d={path}
              fill={slice.color}
              className={`usage-pie-slice ${hoveredKey === slice.key ? "active" : ""}`}
              transform={
                hoveredKey === slice.key
                  ? `translate(${Math.cos(slice.midAngle) * 6} ${Math.sin(slice.midAngle) * 6})`
                  : undefined
              }
              onMouseEnter={() => setHoveredKey(slice.key)}
              onMouseLeave={() => setHoveredKey("")}
            >
              <title>
                {slice.label} | Input tokens: {formatNumber(slice.tokensInput)} | Output tokens:{" "}
                {formatNumber(slice.tokensOutput)} | Budget used: {formatCost(slice.costUsd)}
              </title>
            </path>
          );
        })}
        <circle cx={center} cy={center} r={innerRadius - 1} className="usage-pie-hole" />
      </svg>
    </div>
  );
}

function NodeUsageSection({
  title,
  items,
  colorMap,
}: {
  title: string;
  items: NodeUsage[];
  colorMap: Map<string, string>;
}) {
  return (
    <section className="usage-modal-section">
      <h3>{title}</h3>
      <PieChart title={title} items={items} colorMap={colorMap} />
    </section>
  );
}

export function UsageDetailsModal({
  isOpen,
  latestRun,
  sessionNodeUsage,
  onClose,
}: UsageDetailsModalProps) {
  const latestRunNodeUsage = latestRun?.metrics.node_usage ?? [];
  const legendNodes = useMemo(() => {
    const seen = new Set<string>();
    const merged = [...latestRunNodeUsage, ...sessionNodeUsage];
    return merged.filter((item) => {
      if (seen.has(item.agent_node)) {
        return false;
      }
      seen.add(item.agent_node);
      return true;
    });
  }, [latestRunNodeUsage, sessionNodeUsage]);
  const colorMap = useMemo(() => buildColorMap(legendNodes), [legendNodes]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="usage-modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="usage-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Node usage details"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="usage-modal-header">
          <h2>Node Usage Details</h2>
          <button className="button-muted" type="button" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="usage-modal-grid">
          <NodeUsageSection title="Latest run" items={latestRunNodeUsage} colorMap={colorMap} />
          <NodeUsageSection
            title="Session consolidated"
            items={sessionNodeUsage}
            colorMap={colorMap}
          />
        </div>
        <ul className="usage-pie-legend shared">
          {legendNodes.map((node) => (
            <li key={`legend-${node.agent_node}`} className="usage-pie-legend-item">
              <span
                className="usage-pie-dot"
                style={{ background: colorMap.get(node.agent_node) ?? PIE_COLORS[0] }}
              />
              <span className="usage-node-name" title={node.agent_node}>
                {compactNodeLabel(node.agent_node)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
