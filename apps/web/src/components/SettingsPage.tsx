import { ReactNode, useEffect, useState } from "react";
import {
  NodeConfig,
  SettingsNodes,
  SettingsUpdate,
  useGetSettingsQuery,
} from "../store/api/settingsApi";

// ── types ──────────────────────────────────────────────────────────────────

type SettingsPageProps = {
  onClose: () => void;
};

type SettingsSectionProps = {
  title: string;
  description: string;
  children?: ReactNode;
};

type NodeErrors = Partial<Record<keyof SettingsNodes, { model_id?: string; prompt_version?: string }>>;

// ── helpers ────────────────────────────────────────────────────────────────

const NODE_LABELS: Record<keyof SettingsNodes, string> = {
  scope: "Scope Checker",
  planner: "Planner",
  clarifier: "Clarifier",
  answer: "Answer Synthesizer",
  summarizer: "Summarizer",
  injection_classifier: "Injection Classifier",
};

const NODE_KEYS = Object.keys(NODE_LABELS) as (keyof SettingsNodes)[];

function validateNodes(nodes: SettingsNodes): NodeErrors {
  const errors: NodeErrors = {};
  for (const key of NODE_KEYS) {
    const node = nodes[key];
    const e: { model_id?: string; prompt_version?: string } = {};
    if (!node.model_id.trim()) e.model_id = "Required";
    if (!node.prompt_version.trim()) e.prompt_version = "Required";
    if (e.model_id || e.prompt_version) errors[key] = e;
  }
  return errors;
}

// ── shared section shell ───────────────────────────────────────────────────

function SettingsSection({ title, description, children }: SettingsSectionProps) {
  return (
    <section className="settings-section">
      <div className="settings-section-label">
        <h2 className="settings-section-title">{title}</h2>
        <p className="settings-section-desc">{description}</p>
      </div>
      <div className="settings-section-body">
        {children ?? <p className="settings-coming-soon">Coming in a future slice.</p>}
      </div>
    </section>
  );
}

// ── model config section ───────────────────────────────────────────────────

type ModelConfigSectionProps = {
  nodes: SettingsNodes;
  errors: NodeErrors;
  onChange: (nodes: SettingsNodes) => void;
};

function ModelConfigSection({ nodes, errors, onChange }: ModelConfigSectionProps) {
  function setNode(key: keyof SettingsNodes, patch: Partial<NodeConfig>) {
    onChange({ ...nodes, [key]: { ...nodes[key], ...patch } });
  }

  return (
    <div className="model-config-grid">
      <div className="model-config-header">
        <span>Node</span>
        <span>Model ID</span>
        <span>Prompt Version</span>
      </div>
      {NODE_KEYS.map((key) => {
        const node = nodes[key];
        const err = errors[key];
        return (
          <div key={key} className="model-config-row">
            <span className="model-config-node-label">{NODE_LABELS[key]}</span>
            <div className="settings-field">
              <input
                className={`settings-input${err?.model_id ? " settings-input-error" : ""}`}
                value={node.model_id}
                onChange={(e: { target: { value: string } }) => setNode(key, { model_id: e.target.value })}
                placeholder="e.g. anthropic.claude-3-haiku-20240307-v1:0"
                spellCheck={false}
              />
              {err?.model_id && <span className="settings-field-error">{err.model_id}</span>}
            </div>
            <div className="settings-field">
              <input
                className={`settings-input${err?.prompt_version ? " settings-input-error" : ""}`}
                value={node.prompt_version}
                onChange={(e: { target: { value: string } }) => setNode(key, { prompt_version: e.target.value })}
                placeholder="e.g. latest"
                spellCheck={false}
              />
              {err?.prompt_version && <span className="settings-field-error">{err.prompt_version}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── execution limits section ───────────────────────────────────────────────

type LimitsErrors = {
  max_agent_steps?: string;
  max_budget_usd?: string;
};

function validateLimits(steps: string, budget: string): LimitsErrors {
  const errors: LimitsErrors = {};
  const stepsNum = Number(steps);
  if (!steps.trim() || !Number.isInteger(stepsNum) || stepsNum < 1) {
    errors.max_agent_steps = "Must be a whole number ≥ 1";
  }
  if (budget.trim() !== "" && (isNaN(Number(budget)) || Number(budget) < 0)) {
    errors.max_budget_usd = "Must be a number ≥ 0, or leave blank for unlimited";
  }
  return errors;
}

type ExecutionLimitsSectionProps = {
  steps: string;
  budget: string;
  errors: LimitsErrors;
  onStepsChange: (v: string) => void;
  onBudgetChange: (v: string) => void;
};

function ExecutionLimitsSection({ steps, budget, errors, onStepsChange, onBudgetChange }: ExecutionLimitsSectionProps) {
  return (
    <div className="limits-grid">
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">Max Agent Steps</span>
          <span className="limits-field-unit">steps</span>
        </div>
        <div className="settings-field">
          <input
            className={`settings-input limits-input${errors.max_agent_steps ? " settings-input-error" : ""}`}
            value={steps}
            onChange={(e: { target: { value: string } }) => onStepsChange(e.target.value)}
            inputMode="numeric"
            placeholder="10"
          />
          {errors.max_agent_steps && <span className="settings-field-error">{errors.max_agent_steps}</span>}
        </div>
      </div>
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">Max Budget</span>
          <span className="limits-field-unit">USD — blank = unlimited</span>
        </div>
        <div className="settings-field">
          <input
            className={`settings-input limits-input${errors.max_budget_usd ? " settings-input-error" : ""}`}
            value={budget}
            onChange={(e: { target: { value: string } }) => onBudgetChange(e.target.value)}
            inputMode="decimal"
            placeholder="unlimited"
          />
          {errors.max_budget_usd && <span className="settings-field-error">{errors.max_budget_usd}</span>}
        </div>
      </div>
    </div>
  );
}

// ── page ───────────────────────────────────────────────────────────────────

const DEFAULT_NODE: NodeConfig = { model_id: "", prompt_version: "latest" };
const DEFAULT_NODES: SettingsNodes = {
  scope: DEFAULT_NODE,
  planner: DEFAULT_NODE,
  clarifier: DEFAULT_NODE,
  answer: DEFAULT_NODE,
  summarizer: DEFAULT_NODE,
  injection_classifier: DEFAULT_NODE,
};

export function SettingsPage({ onClose }: SettingsPageProps) {
  const { data, isLoading, isError } = useGetSettingsQuery();

  const [draft, setDraft] = useState<SettingsUpdate | null>(null);
  const [nodeErrors, setNodeErrors] = useState<NodeErrors>({});

  const [stepsRaw, setStepsRaw] = useState("");
  const [budgetRaw, setBudgetRaw] = useState("");
  const [limitsErrors, setLimitsErrors] = useState<LimitsErrors>({});

  useEffect(() => {
    if (data && !draft) {
      const { id: _id, schema_version: _sv, ...editable } = data;
      setDraft(editable);
      setStepsRaw(String(editable.max_agent_steps));
      setBudgetRaw(editable.max_budget_usd != null ? String(editable.max_budget_usd) : "");
    }
  }, [data, draft]);

  function handleNodesChange(nodes: SettingsNodes) {
    if (!draft) return;
    const errors = validateNodes(nodes);
    setNodeErrors(errors);
    setDraft({ ...draft, nodes });
  }

  function handleStepsChange(v: string) {
    setStepsRaw(v);
    const errors = validateLimits(v, budgetRaw);
    setLimitsErrors(errors);
    if (!errors.max_agent_steps && draft) {
      setDraft({ ...draft, max_agent_steps: Number(v) });
    }
  }

  function handleBudgetChange(v: string) {
    setBudgetRaw(v);
    const errors = validateLimits(stepsRaw, v);
    setLimitsErrors(errors);
    if (!errors.max_budget_usd && draft) {
      setDraft({ ...draft, max_budget_usd: v.trim() === "" ? null : Number(v) });
    }
  }

  return (
    <div className="settings-page">
      <header className="settings-header">
        <button
          type="button"
          className="settings-back button-muted"
          aria-label="Back to chat"
          onClick={onClose}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M19 12H5" />
            <path d="M12 19l-7-7 7-7" />
          </svg>
          Back
        </button>
        <h1 className="settings-title">Settings</h1>
        {data && (
          <span className="settings-config-id">config {data.id.slice(0, 8)}</span>
        )}
      </header>

      {isLoading && <p className="settings-status">Loading…</p>}
      {isError && <p className="settings-status settings-status-error">Failed to load settings.</p>}

      {!isLoading && !isError && (
        <div className="settings-body">
          <div className="settings-sections">
            <SettingsSection
              title="Model Configuration"
              description="Set the model and prompt version used by each agent node."
            >
              <ModelConfigSection
                nodes={draft?.nodes ?? DEFAULT_NODES}
                errors={nodeErrors}
                onChange={handleNodesChange}
              />
            </SettingsSection>
            <SettingsSection
              title="Execution Limits"
              description="Control the maximum number of steps and per-run budget."
            >
              <ExecutionLimitsSection
                steps={stepsRaw}
                budget={budgetRaw}
                errors={limitsErrors}
                onStepsChange={handleStepsChange}
                onBudgetChange={handleBudgetChange}
              />
            </SettingsSection>
            <SettingsSection
              title="History & Summarization"
              description="Configure how many conversation turns to keep verbatim before compacting."
            />
            <SettingsSection
              title="Evaluation & Sampling"
              description="Tune online eval sampling rate, LLM-as-judge, and RAGAS scoring."
            />
            <SettingsSection
              title="Safety & Injection"
              description="Enable or disable the LLM-based prompt injection classifier."
            />
            <SettingsSection
              title="Agent Hard Limits"
              description="Cap tool calls, LLM calls, and total execution time per run."
            />
          </div>
        </div>
      )}
    </div>
  );
}
