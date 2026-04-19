import { baseApi } from "../baseApi";

export type InfoResponse = {
  readonly: boolean;
  allowed_namespaces: string[];
  tool_server_url: string;
};

export const infoApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getInfo: builder.query<InfoResponse, void>({
      query: () => "/info",
    }),
  }),
  overrideExisting: false,
});

export const { useGetInfoQuery } = infoApi;
