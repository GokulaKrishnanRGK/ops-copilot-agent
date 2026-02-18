{{- define "opscopilot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "opscopilot.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "opscopilot.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "opscopilot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "opscopilot.labels" -}}
helm.sh/chart: {{ include "opscopilot.chart" . }}
app.kubernetes.io/name: {{ include "opscopilot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "opscopilot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "opscopilot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "opscopilot.namespace" -}}
{{- if .Values.global.namespaceOverride -}}
{{ .Values.global.namespaceOverride }}
{{- else -}}
{{ .Release.Namespace }}
{{- end -}}
{{- end -}}

{{- define "opscopilot.serviceAccountName" -}}
{{- if .Values.toolServer.serviceAccount.create -}}
{{- if .Values.toolServer.serviceAccount.name -}}
{{ .Values.toolServer.serviceAccount.name }}
{{- else -}}
{{ printf "%s-tool-server" (include "opscopilot.fullname" .) }}
{{- end -}}
{{- else -}}
default
{{- end -}}
{{- end -}}

{{- define "opscopilot.apiServiceName" -}}
{{ printf "%s-api" (include "opscopilot.fullname" .) }}
{{- end -}}

{{- define "opscopilot.webServiceName" -}}
{{ printf "%s-web" (include "opscopilot.fullname" .) }}
{{- end -}}

{{- define "opscopilot.toolServerServiceName" -}}
{{ printf "%s-tool-server" (include "opscopilot.fullname" .) }}
{{- end -}}
