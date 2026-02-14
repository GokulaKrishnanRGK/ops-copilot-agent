import { ToolCall, ToolCallListResponse } from "../../types";
import { baseApi } from "../baseApi";

export const toolCallApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listToolCalls: builder.query<
      ToolCall[],
      { runId?: string; runIds?: string[]; sessionId?: string }
    >({
      query: ({ runId, runIds, sessionId }) => ({
        url: "/tool-calls",
        params: {
          run_id: runId,
          run_ids: runIds && runIds.length > 0 ? runIds.join(",") : undefined,
          session_id: sessionId,
        },
      }),
      transformResponse: (response: ToolCallListResponse) => response.items,
      providesTags: (_result, _error, { runId, runIds, sessionId }) => [
        { type: "ToolCalls", id: runId ?? runIds?.join("|") ?? sessionId ?? "unknown" },
      ],
    }),
  }),
  overrideExisting: false,
});

export const { useLazyListToolCallsQuery } = toolCallApi;
