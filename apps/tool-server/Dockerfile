FROM golang:1.24-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/tool-server ./cmd/tool-server

FROM alpine:3.21
RUN apk add --no-cache ca-certificates curl
WORKDIR /app
COPY --from=build /out/tool-server /app/tool-server
EXPOSE 8080
ENTRYPOINT ["/app/tool-server"]
