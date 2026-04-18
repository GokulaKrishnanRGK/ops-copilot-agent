import { baseApi } from "../baseApi";

export type NodeConfig = {
  model_id: string;
  prompt_version: string;
};

export type SettingsNodes = {
  scope: NodeConfig;
  planner: NodeConfig;
  clarifier: NodeConfig;
  answer: NodeConfig;
  summarizer: NodeConfig;
  injection_classifier: NodeConfig;
};

export type SettingsResponse = {
  id: string;
  schema_version: string;
  nodes: SettingsNodes;
  max_agent_steps: number;
  max_budget_usd: number | null;
  history_window_turns: number;
  summarizer_prompt_version: string;
  eval_sample_rate: number;
  eval_llm_judge_enabled: boolean;
  eval_ragas_enabled: boolean;
  eval_judge_model_id: string;
  prompt_injection_llm_check: boolean;
  agent_max_tool_calls: number;
  agent_max_llm_calls: number;
  agent_max_execution_time_ms: number;
  bedrock_embedding_model_id: string;
};

export type SettingsUpdate = Omit<SettingsResponse, "id" | "schema_version">;

export const settingsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getSettings: builder.query<SettingsResponse, void>({
      query: () => "/settings",
      providesTags: ["Settings"],
    }),
    patchSettings: builder.mutation<SettingsResponse, SettingsUpdate>({
      query: (body) => ({
        url: "/settings",
        method: "PATCH",
        body,
      }),
      invalidatesTags: ["Settings"],
    }),
  }),
  overrideExisting: false,
});

export const { useGetSettingsQuery, usePatchSettingsMutation } = settingsApi;
