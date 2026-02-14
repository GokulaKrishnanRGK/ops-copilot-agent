import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { webConfig } from "../config";

export const baseApi = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({
    baseUrl: webConfig.apiBaseUrl,
  }),
  endpoints: () => ({}),
  tagTypes: ["Sessions", "Messages", "Runs", "ToolCalls"],
});
