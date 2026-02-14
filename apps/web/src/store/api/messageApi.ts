import { Message, MessageListResponse } from "../../types";
import { baseApi } from "../baseApi";

export const messageApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listMessages: builder.query<
      Message[],
      { sessionId: string; limit?: number; offset?: number; order?: "asc" | "desc" }
    >({
      query: ({ sessionId, limit, offset, order }) => ({
        url: "/messages",
        params: {
          session_id: sessionId,
          limit,
          offset,
          order,
        },
      }),
      transformResponse: (response: MessageListResponse) => response.items,
      providesTags: (_result, _error, { sessionId }) => [{ type: "Messages", id: sessionId }],
    }),
  }),
  overrideExisting: false,
});

export const { useLazyListMessagesQuery } = messageApi;
