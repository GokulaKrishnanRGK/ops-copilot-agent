import { Session, SessionListResponse } from "../../types";
import { buildApiUrl, webConfig } from "../../config";
import { baseApi } from "../baseApi";

export const sessionApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listSessions: builder.query<Session[], { limit: number; offset: number }>({
      query: ({ limit, offset }) => ({
        url: "/sessions",
        params: {
          limit,
          offset,
        },
      }),
      transformResponse: (response: SessionListResponse) => response.items,
      providesTags: ["Sessions"],
    }),
    createSession: builder.mutation<Session, { title: string }>({
      query: (body) => ({
        url: "/sessions",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Sessions"],
    }),
    renameSession: builder.mutation<Session, { sessionId: string; title: string }>({
      query: ({ sessionId, title }) => ({
        url: `/sessions/${sessionId}`,
        method: "PATCH",
        body: { title },
      }),
      invalidatesTags: ["Sessions"],
    }),
    deleteSession: builder.mutation<void, { sessionId: string }>({
      query: ({ sessionId }) => ({
        url: `/sessions/${sessionId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Sessions"],
    }),
  }),
  overrideExisting: false,
});

export const {
  useLazyListSessionsQuery,
  useCreateSessionMutation,
  useRenameSessionMutation,
  useDeleteSessionMutation,
} = sessionApi;

export function sessionStreamUrl(sessionId: string): string {
  return buildApiUrl(`/sessions/${sessionId}${webConfig.streamingEndpoint}`);
}
