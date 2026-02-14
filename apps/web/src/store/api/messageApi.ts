import { Message, MessageListResponse } from "../../types";
import { baseApi } from "../baseApi";

export const messageApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listMessages: builder.query<Message[], { sessionId: string }>({
      query: ({ sessionId }) => ({
        url: "/messages",
        params: {
          session_id: sessionId,
        },
      }),
      transformResponse: (response: MessageListResponse) => response.items,
      providesTags: (_result, _error, { sessionId }) => [{ type: "Messages", id: sessionId }],
    }),
  }),
  overrideExisting: false,
});

export const { useListMessagesQuery } = messageApi;
