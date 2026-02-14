import { Run, RunListResponse, SessionMetrics } from "../../types";
import { baseApi } from "../baseApi";

export type RunsQueryResult = {
  items: Run[];
  sessionMetrics: SessionMetrics;
};

const EMPTY_USAGE = {
  tokens_input: 0,
  tokens_output: 0,
  tokens_total: 0,
  cost_usd: 0,
  llm_call_count: 0,
};

const EMPTY_BUDGET = {
  total_usd: 0,
  delta_usd: 0,
  event_count: 0,
};

const EMPTY_SESSION_METRICS: SessionMetrics = {
  usage: EMPTY_USAGE,
  budget: EMPTY_BUDGET,
  run_count: 0,
};

export const runApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listRuns: builder.query<RunsQueryResult, { sessionId: string }>({
      query: ({ sessionId }) => ({
        url: "/runs",
        params: {
          session_id: sessionId,
        },
      }),
      transformResponse: (response: RunListResponse): RunsQueryResult => ({
        items: response.items,
        sessionMetrics: response.session_metrics ?? EMPTY_SESSION_METRICS,
      }),
      providesTags: (_result, _error, { sessionId }) => [{ type: "Runs", id: sessionId }],
    }),
  }),
  overrideExisting: false,
});

export const { useListRunsQuery } = runApi;
