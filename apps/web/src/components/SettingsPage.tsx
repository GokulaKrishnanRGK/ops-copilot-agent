import { ReactNode, useEffect, useRef, useState } from "react";
import {
  NodeConfig,
  SettingsNodes,
  SettingsUpdate,
  useGetSettingsQuery,
  usePatchSettingsMutation,
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

type LimitsErrors = {
  max_agent_steps?: string;
  max_budget_usd?: string;
};

type HistoryErrors = {
  history_window_turns?: string;
};

type EvalErrors = {
  eval_sample_rate?: string;
  eval_judge_model_id?: string;
};

type HardLimitErrors = {
  agent_max_tool_calls?: string;
  agent_max_llm_calls?: string;
  agent_max_execution_time_ms?: string;
};

type EmbeddingErrors = {
  bedrock_embedding_model_id?: string;
};

// ── validators ─────────────────────────────────────────────────────────────

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

function validateLimits(steps: string, budget: string): LimitsErrors {
  const errors: LimitsErrors = {};
  const stepsNum = Number(steps);
  if (!steps.trim() || !Number.isInteger(stepsNum) || stepsNum < 1)
    errors.max_agent_steps = "Must be a whole number ≥ 1";
  if (budget.trim() !== "" && (isNaN(Number(budget)) || Number(budget) < 0))
    errors.max_budget_usd = "Must be a number ≥ 0, or leave blank for unlimited";
  return errors;
}

function validateHistory(window: string): HistoryErrors {
  const errors: HistoryErrors = {};
  const n = Number(window);
  if (!window.trim() || !Number.isInteger(n) || n < 1)
    errors.history_window_turns = "Must be a whole number ≥ 1";
  return errors;
}

function validateEval(sampleRate: string, judgeModelId: string): EvalErrors {
  const errors: EvalErrors = {};
  const rate = Number(sampleRate);
  if (sampleRate.trim() === "" || isNaN(rate) || rate < 0 || rate > 1)
    errors.eval_sample_rate = "Must be a number between 0 and 1";
  if (!judgeModelId.trim()) errors.eval_judge_model_id = "Required";
  return errors;
}

function validateHardLimits(toolCalls: string, llmCalls: string, execTime: string): HardLimitErrors {
  const errors: HardLimitErrors = {};
  const tc = Number(toolCalls);
  const lc = Number(llmCalls);
  const et = Number(execTime);
  if (!toolCalls.trim() || !Number.isInteger(tc) || tc < 1) errors.agent_max_tool_calls = "Must be a whole number ≥ 1";
  if (!llmCalls.trim() || !Number.isInteger(lc) || lc < 1) errors.agent_max_llm_calls = "Must be a whole number ≥ 1";
  if (!execTime.trim() || !Number.isInteger(et) || et < 1) errors.agent_max_execution_time_ms = "Must be a whole number ≥ 1";
  return errors;
}

function hasErrors(...errorMaps: object[]): boolean {
  return errorMaps.some((e) => Object.keys(e).length > 0);
}

// ── shared components ──────────────────────────────────────────────────────

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

type ToggleProps = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
};

function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      className={`settings-toggle${checked ? " settings-toggle--on" : ""}`}
      onClick={() => onChange(!checked)}
      aria-label={label}
    >
      <span className="settings-toggle-thumb" />
    </button>
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

// ── history & summarization section ───────────────────────────────────────

type HistorySectionProps = {
  historyWindow: string;
  summarizerVersion: string;
  errors: HistoryErrors;
  onWindowChange: (v: string) => void;
  onVersionChange: (v: string) => void;
};

function HistorySummarizationSection({ historyWindow, summarizerVersion, errors, onWindowChange, onVersionChange }: HistorySectionProps) {
  return (
    <div className="limits-grid">
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">History Window</span>
          <span className="limits-field-unit">turns kept verbatim</span>
        </div>
        <div className="settings-field">
          <input
            className={`settings-input limits-input${errors.history_window_turns ? " settings-input-error" : ""}`}
            value={historyWindow}
            onChange={(e: { target: { value: string } }) => onWindowChange(e.target.value)}
            inputMode="numeric"
            placeholder="6"
          />
          {errors.history_window_turns && <span className="settings-field-error">{errors.history_window_turns}</span>}
        </div>
      </div>
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">Summarizer Version</span>
          <span className="limits-field-unit">prompt version</span>
        </div>
        <div className="settings-field">
          <input
            className="settings-input limits-input"
            value={summarizerVersion}
            onChange={(e: { target: { value: string } }) => onVersionChange(e.target.value)}
            placeholder="latest"
            spellCheck={false}
          />
        </div>
      </div>
    </div>
  );
}

// ── evaluation & sampling section ─────────────────────────────────────────

type EvalSectionProps = {
  sampleRate: string;
  llmJudgeEnabled: boolean;
  ragasEnabled: boolean;
  judgeModelId: string;
  errors: EvalErrors;
  onSampleRateChange: (v: string) => void;
  onLlmJudgeChange: (v: boolean) => void;
  onRagasChange: (v: boolean) => void;
  onJudgeModelChange: (v: string) => void;
};

function EvalSamplingSection({
  sampleRate, llmJudgeEnabled, ragasEnabled, judgeModelId, errors,
  onSampleRateChange, onLlmJudgeChange, onRagasChange, onJudgeModelChange,
}: EvalSectionProps) {
  return (
    <div className="limits-grid">
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">Sample Rate</span>
          <span className="limits-field-unit">0.0 – 1.0 (0 = off)</span>
        </div>
        <div className="settings-field">
          <input
            className={`settings-input limits-input${errors.eval_sample_rate ? " settings-input-error" : ""}`}
            value={sampleRate}
            onChange={(e: { target: { value: string } }) => onSampleRateChange(e.target.value)}
            inputMode="decimal"
            placeholder="0.1"
          />
          {errors.eval_sample_rate && <span className="settings-field-error">{errors.eval_sample_rate}</span>}
        </div>
      </div>
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">LLM-as-Judge</span>
          <span className="limits-field-unit">evaluate answer quality</span>
        </div>
        <div className="settings-toggle-row">
          <Toggle checked={llmJudgeEnabled} onChange={onLlmJudgeChange} label="Enable LLM-as-judge scoring" />
        </div>
      </div>
      {llmJudgeEnabled && (
        <div className="limits-row settings-conditional">
          <div className="limits-row-label">
            <span className="limits-field-name">Judge Model ID</span>
            <span className="limits-field-unit">model used for scoring</span>
          </div>
          <div className="settings-field">
            <input
              className={`settings-input${errors.eval_judge_model_id ? " settings-input-error" : ""}`}
              value={judgeModelId}
              onChange={(e: { target: { value: string } }) => onJudgeModelChange(e.target.value)}
              placeholder="anthropic.claude-3-haiku-20240307-v1:0"
              spellCheck={false}
            />
            {errors.eval_judge_model_id && <span className="settings-field-error">{errors.eval_judge_model_id}</span>}
          </div>
        </div>
      )}
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">RAGAS Scoring</span>
          <span className="limits-field-unit">evaluate RAG retrieval</span>
        </div>
        <div className="settings-toggle-row">
          <Toggle checked={ragasEnabled} onChange={onRagasChange} label="Enable RAGAS scoring" />
        </div>
      </div>
    </div>
  );
}

// ── safety & injection section ─────────────────────────────────────────────

type SafetySectionProps = {
  llmCheckEnabled: boolean;
  onChange: (v: boolean) => void;
};

function SafetyInjectionSection({ llmCheckEnabled, onChange }: SafetySectionProps) {
  return (
    <div className="limits-grid">
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">LLM Injection Check</span>
          <span className="limits-field-unit">classifier layer 3</span>
        </div>
        <div className="settings-toggle-row">
          <Toggle checked={llmCheckEnabled} onChange={onChange} label="Enable LLM-based prompt injection classifier" />
        </div>
      </div>
      {llmCheckEnabled && (
        <p className="limits-field-unit settings-conditional">
          Injection classifier model ID is configured in <strong>Model Configuration</strong> above.
        </p>
      )}
    </div>
  );
}

// ── embedding configuration section ───────────────────────────────────────

type EmbeddingConfigSectionProps = {
  modelId: string;
  error?: string;
  onChange: (v: string) => void;
};

function EmbeddingConfigSection({ modelId, error, onChange }: EmbeddingConfigSectionProps) {
  return (
    <div className="limits-grid">
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">Bedrock Embedding Model</span>
          <span className="limits-field-unit">model ID for RAG retrieval</span>
        </div>
        <div className="settings-field">
          <input
            className={`settings-input${error ? " settings-input-error" : ""}`}
            value={modelId}
            onChange={(e: { target: { value: string } }) => onChange(e.target.value)}
            placeholder="amazon.titan-embed-text-v1"
            spellCheck={false}
          />
          {error && <span className="settings-field-error">{error}</span>}
        </div>
      </div>
    </div>
  );
}

// ── agent hard limits section ──────────────────────────────────────────────

type HardLimitsSectionProps = {
  toolCalls: string;
  llmCalls: string;
  execTime: string;
  errors: HardLimitErrors;
  onToolCallsChange: (v: string) => void;
  onLlmCallsChange: (v: string) => void;
  onExecTimeChange: (v: string) => void;
};

function AgentHardLimitsSection({ toolCalls, llmCalls, execTime, errors, onToolCallsChange, onLlmCallsChange, onExecTimeChange }: HardLimitsSectionProps) {
  return (
    <div className="limits-grid">
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">Max Tool Calls</span>
          <span className="limits-field-unit">calls per run</span>
        </div>
        <div className="settings-field">
          <input
            className={`settings-input limits-input${errors.agent_max_tool_calls ? " settings-input-error" : ""}`}
            value={toolCalls}
            onChange={(e: { target: { value: string } }) => onToolCallsChange(e.target.value)}
            inputMode="numeric"
            placeholder="10"
          />
          {errors.agent_max_tool_calls && <span className="settings-field-error">{errors.agent_max_tool_calls}</span>}
        </div>
      </div>
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">Max LLM Calls</span>
          <span className="limits-field-unit">calls per run</span>
        </div>
        <div className="settings-field">
          <input
            className={`settings-input limits-input${errors.agent_max_llm_calls ? " settings-input-error" : ""}`}
            value={llmCalls}
            onChange={(e: { target: { value: string } }) => onLlmCallsChange(e.target.value)}
            inputMode="numeric"
            placeholder="10"
          />
          {errors.agent_max_llm_calls && <span className="settings-field-error">{errors.agent_max_llm_calls}</span>}
        </div>
      </div>
      <div className="limits-row">
        <div className="limits-row-label">
          <span className="limits-field-name">Max Execution Time</span>
          <span className="limits-field-unit">ms per run</span>
        </div>
        <div className="settings-field">
          <input
            className={`settings-input limits-input${errors.agent_max_execution_time_ms ? " settings-input-error" : ""}`}
            value={execTime}
            onChange={(e: { target: { value: string } }) => onExecTimeChange(e.target.value)}
            inputMode="numeric"
            placeholder="30000"
          />
          {errors.agent_max_execution_time_ms && <span className="settings-field-error">{errors.agent_max_execution_time_ms}</span>}
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
  const [patchSettings, { isLoading: isSaving }] = usePatchSettingsMutation();

  const [draft, setDraft] = useState<SettingsUpdate | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [nodeErrors, setNodeErrors] = useState<NodeErrors>({});
  const [stepsRaw, setStepsRaw] = useState("");
  const [budgetRaw, setBudgetRaw] = useState("");
  const [limitsErrors, setLimitsErrors] = useState<LimitsErrors>({});
  const [historyWindowRaw, setHistoryWindowRaw] = useState("");
  const [historyErrors, setHistoryErrors] = useState<HistoryErrors>({});
  const [evalSampleRateRaw, setEvalSampleRateRaw] = useState("");
  const [evalErrors, setEvalErrors] = useState<EvalErrors>({});
  const [toolCallsRaw, setToolCallsRaw] = useState("");
  const [llmCallsRaw, setLlmCallsRaw] = useState("");
  const [execTimeRaw, setExecTimeRaw] = useState("");
  const [hardLimitErrors, setHardLimitErrors] = useState<HardLimitErrors>({});
  const [embeddingErrors, setEmbeddingErrors] = useState<EmbeddingErrors>({});

  useEffect(() => {
    if (data && !draft) {
      const { id: _id, schema_version: _sv, ...editable } = data;
      setDraft(editable);
      setStepsRaw(String(editable.max_agent_steps));
      setBudgetRaw(editable.max_budget_usd != null ? String(editable.max_budget_usd) : "");
      setHistoryWindowRaw(String(editable.history_window_turns));
      setEvalSampleRateRaw(String(editable.eval_sample_rate));
      setToolCallsRaw(String(editable.agent_max_tool_calls));
      setLlmCallsRaw(String(editable.agent_max_llm_calls));
      setExecTimeRaw(String(editable.agent_max_execution_time_ms));
    }
  }, [data, draft]);

  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

  useEffect(() => {
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, []);

  function handleClose() {
    if (isDirty && !window.confirm("You have unsaved changes. Leave without saving?")) return;
    onClose();
  }

  async function handleSave() {
    if (!draft) return;

    const nErrors = validateNodes(draft.nodes);
    const lErrors = validateLimits(stepsRaw, budgetRaw);
    const hErrors = validateHistory(historyWindowRaw);
    const eErrors = validateEval(evalSampleRateRaw, draft.eval_judge_model_id);
    const hlErrors = validateHardLimits(toolCallsRaw, llmCallsRaw, execTimeRaw);
    const embErrors: EmbeddingErrors = !draft.bedrock_embedding_model_id.trim()
      ? { bedrock_embedding_model_id: "Required" }
      : {};

    setNodeErrors(nErrors);
    setLimitsErrors(lErrors);
    setHistoryErrors(hErrors);
    setEvalErrors(eErrors);
    setHardLimitErrors(hlErrors);
    setEmbeddingErrors(embErrors);

    if (hasErrors(nErrors, lErrors, hErrors, eErrors, hlErrors, embErrors)) return;

    setSaveError(null);

    try {
      await patchSettings(draft).unwrap();
      setIsDirty(false);
      setSaveSuccess(true);
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
      successTimerRef.current = setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: unknown) {
      let message = "Save failed. Please try again.";
      if (err && typeof err === "object") {
        const errObj = err as Record<string, unknown>;
        if (errObj.data && typeof errObj.data === "object") {
          const errData = errObj.data as Record<string, unknown>;
          if (typeof errData.detail === "string") message = errData.detail;
        }
      }
      setSaveError(message);
    }
  }

  function handleNodesChange(nodes: SettingsNodes) {
    if (!draft) return;
    setIsDirty(true);
    setNodeErrors(validateNodes(nodes));
    setDraft({ ...draft, nodes });
  }

  function handleStepsChange(v: string) {
    setIsDirty(true);
    setStepsRaw(v);
    const errors = validateLimits(v, budgetRaw);
    setLimitsErrors(errors);
    if (!errors.max_agent_steps && draft) setDraft({ ...draft, max_agent_steps: Number(v) });
  }

  function handleBudgetChange(v: string) {
    setIsDirty(true);
    setBudgetRaw(v);
    const errors = validateLimits(stepsRaw, v);
    setLimitsErrors(errors);
    if (!errors.max_budget_usd && draft)
      setDraft({ ...draft, max_budget_usd: v.trim() === "" ? null : Number(v) });
  }

  function handleHistoryWindowChange(v: string) {
    setIsDirty(true);
    setHistoryWindowRaw(v);
    const errors = validateHistory(v);
    setHistoryErrors(errors);
    if (!errors.history_window_turns && draft) setDraft({ ...draft, history_window_turns: Number(v) });
  }

  function handleSummarizerVersionChange(v: string) {
    if (!draft) return;
    setIsDirty(true);
    setDraft({ ...draft, summarizer_prompt_version: v });
  }

  function handleEvalSampleRateChange(v: string) {
    setIsDirty(true);
    setEvalSampleRateRaw(v);
    const errors = validateEval(v, draft?.eval_judge_model_id ?? "");
    setEvalErrors(errors);
    if (!errors.eval_sample_rate && draft) setDraft({ ...draft, eval_sample_rate: Number(v) });
  }

  function handleLlmJudgeChange(v: boolean) {
    if (!draft) return;
    setIsDirty(true);
    setDraft({ ...draft, eval_llm_judge_enabled: v });
  }

  function handleRagasChange(v: boolean) {
    if (!draft) return;
    setIsDirty(true);
    setDraft({ ...draft, eval_ragas_enabled: v });
  }

  function handleJudgeModelChange(v: string) {
    if (!draft) return;
    setIsDirty(true);
    const errors = validateEval(evalSampleRateRaw, v);
    setEvalErrors(errors);
    setDraft({ ...draft, eval_judge_model_id: v });
  }

  function handleInjectionCheckChange(v: boolean) {
    if (!draft) return;
    setIsDirty(true);
    setDraft({ ...draft, prompt_injection_llm_check: v });
  }

  function handleToolCallsChange(v: string) {
    setIsDirty(true);
    setToolCallsRaw(v);
    const errors = validateHardLimits(v, llmCallsRaw, execTimeRaw);
    setHardLimitErrors(errors);
    if (!errors.agent_max_tool_calls && draft) setDraft({ ...draft, agent_max_tool_calls: Number(v) });
  }

  function handleLlmCallsChange(v: string) {
    setIsDirty(true);
    setLlmCallsRaw(v);
    const errors = validateHardLimits(toolCallsRaw, v, execTimeRaw);
    setHardLimitErrors(errors);
    if (!errors.agent_max_llm_calls && draft) setDraft({ ...draft, agent_max_llm_calls: Number(v) });
  }

  function handleExecTimeChange(v: string) {
    setIsDirty(true);
    setExecTimeRaw(v);
    const errors = validateHardLimits(toolCallsRaw, llmCallsRaw, v);
    setHardLimitErrors(errors);
    if (!errors.agent_max_execution_time_ms && draft) setDraft({ ...draft, agent_max_execution_time_ms: Number(v) });
  }

  function handleEmbeddingModelChange(v: string) {
    if (!draft) return;
    setIsDirty(true);
    const embErrors: EmbeddingErrors = !v.trim() ? { bedrock_embedding_model_id: "Required" } : {};
    setEmbeddingErrors(embErrors);
    setDraft({ ...draft, bedrock_embedding_model_id: v });
  }

  return (
    <div className="settings-page">
      <header className="settings-header">
        <button
          type="button"
          className="settings-back button-muted"
          aria-label="Back to chat"
          onClick={handleClose}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M19 12H5" />
            <path d="M12 19l-7-7 7-7" />
          </svg>
          Back
        </button>
        <h1 className="settings-title">Settings</h1>
        {data && (
          <span className="settings-config-id">
            {data.schema_version} · {data.id.slice(0, 8)}
          </span>
        )}
      </header>

      {isLoading && <p className="settings-status">Loading…</p>}
      {isError && <p className="settings-status settings-status-error">Failed to load settings.</p>}

      {!isLoading && !isError && (
        <div className="settings-body">
          {saveSuccess && (
            <div className="settings-success-toast" role="status">
              <svg className="settings-success-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Settings saved successfully.
            </div>
          )}
          {saveError && (
            <div className="settings-error-banner" role="alert">
              <span className="settings-error-banner-text">{saveError}</span>
              <button
                type="button"
                className="settings-error-dismiss"
                aria-label="Dismiss error"
                onClick={() => setSaveError(null)}
              >
                ×
              </button>
            </div>
          )}

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
            >
              <HistorySummarizationSection
                historyWindow={historyWindowRaw}
                summarizerVersion={draft?.summarizer_prompt_version ?? "latest"}
                errors={historyErrors}
                onWindowChange={handleHistoryWindowChange}
                onVersionChange={handleSummarizerVersionChange}
              />
            </SettingsSection>
            <SettingsSection
              title="Evaluation & Sampling"
              description="Tune online eval sampling rate, LLM-as-judge, and RAGAS scoring."
            >
              <EvalSamplingSection
                sampleRate={evalSampleRateRaw}
                llmJudgeEnabled={draft?.eval_llm_judge_enabled ?? true}
                ragasEnabled={draft?.eval_ragas_enabled ?? true}
                judgeModelId={draft?.eval_judge_model_id ?? ""}
                errors={evalErrors}
                onSampleRateChange={handleEvalSampleRateChange}
                onLlmJudgeChange={handleLlmJudgeChange}
                onRagasChange={handleRagasChange}
                onJudgeModelChange={handleJudgeModelChange}
              />
            </SettingsSection>
            <SettingsSection
              title="Safety & Injection"
              description="Enable or disable the LLM-based prompt injection classifier."
            >
              <SafetyInjectionSection
                llmCheckEnabled={draft?.prompt_injection_llm_check ?? false}
                onChange={handleInjectionCheckChange}
              />
            </SettingsSection>
            <SettingsSection
              title="Agent Hard Limits"
              description="Cap tool calls, LLM calls, and total execution time per run."
            >
              <AgentHardLimitsSection
                toolCalls={toolCallsRaw}
                llmCalls={llmCallsRaw}
                execTime={execTimeRaw}
                errors={hardLimitErrors}
                onToolCallsChange={handleToolCallsChange}
                onLlmCallsChange={handleLlmCallsChange}
                onExecTimeChange={handleExecTimeChange}
              />
            </SettingsSection>
            <SettingsSection
              title="Embedding Configuration"
              description="Bedrock model used for RAG document retrieval embeddings."
            >
              <EmbeddingConfigSection
                modelId={draft?.bedrock_embedding_model_id ?? ""}
                error={embeddingErrors.bedrock_embedding_model_id}
                onChange={handleEmbeddingModelChange}
              />
            </SettingsSection>
          </div>

          <div className="settings-save-bar">
            {isDirty && <span className="settings-dirty-hint">Unsaved changes</span>}
            <button
              type="button"
              className="settings-save-btn"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <span className="settings-save-spinner" aria-hidden="true" />
                  Saving…
                </>
              ) : (
                "Save"
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
