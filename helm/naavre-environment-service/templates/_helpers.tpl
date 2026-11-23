{{/*
Expand the name of the chart.
*/}}
{{- define "naavre-environment-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "naavre-environment-service.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "naavre-environment-service.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "naavre-environment-service.labels" -}}
helm.sh/chart: {{ include "naavre-environment-service.chart" . }}
{{ include "naavre-environment-service.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "naavre-environment-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "naavre-environment-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "naavre-environment-service.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "naavre-environment-service.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Name of the configmap holding the last image_rebuilder_hook.key for which the
image rebuilder hook succeeded
*/}}
{{- define "naavre-environment-service.imageRebuilderStateName" -}}
{{- printf "%s-image-rebuilder-state" (include "naavre-environment-service.fullname" . | trunc 35 | trimSuffix "-") }}
{{- end }}

{{/*
Value of image_rebuilder_hook.key
*/}}
{{- define "naavre-environment-service.imageRebuilderKey" -}}
{{- .Values.image_rebuilder_hook.key | default "" | toString -}}
{{- end }}

{{/*
Whether the image rebuilder hook should run. Returns "true" or "".

The hook runs:
- on install
- on upgrade, if image_rebuilder_hook.key differs from the key stored by the
  last successful run of the hook.
*/}}
{{- define "naavre-environment-service.imageRebuilderShouldRun" -}}
{{- if .Values.image_rebuilder_hook.enabled -}}
{{- if .Release.IsInstall -}}
true
{{- else -}}
{{- $state := lookup "v1" "ConfigMap" .Release.Namespace (include "naavre-environment-service.imageRebuilderStateName" .) -}}
{{- $previousKey := "" -}}
{{- $hasPrevious := false -}}
{{- if and $state $state.data (hasKey $state.data "key") -}}
{{- $previousKey = index $state.data "key" -}}
{{- $hasPrevious = true -}}
{{- end -}}
{{- if or (not $hasPrevious) (ne $previousKey (include "naavre-environment-service.imageRebuilderKey" .)) -}}
true
{{- end -}}
{{- end -}}
{{- end -}}
{{- end }}
