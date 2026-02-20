#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

external_dns_out="${EXTERNALDNS_VALUES_OUT:-${repo_root}/deploy/helm/external-dns/values-eks.generated.yaml}"
awslbc_out="${AWSLBC_VALUES_OUT:-${repo_root}/deploy/helm/aws-load-balancer-controller/values-eks.generated.yaml}"

mkdir -p "$(dirname "${external_dns_out}")" "$(dirname "${awslbc_out}")"

tf_output_json="$(
  TF_ENV="${TF_ENV:-dev}" \
  TF_VARS_FILE="${TF_VARS_FILE:-deploy/terraform/environments/${TF_ENV:-dev}.tfvars}" \
  TF_STATE_KEY="${TF_STATE_KEY:-ops-copilot/${TF_ENV:-dev}/terraform.tfstate}" \
  bash "${repo_root}/scripts/terraform.sh" output
)"

json_get() {
  local expr="$1"
  printf "%s" "${tf_output_json}" | jq -r "${expr} // empty"
}

aws_region="$(json_get '.helm_values.value.global.awsRegion')"
vpc_id="$(json_get '.network.value.vpc_id')"
external_dns_role_arn="$(json_get '.helm_values.value.controllers.externalDns.roleArn')"
awslbc_role_arn="$(json_get '.helm_values.value.controllers.awsLoadBalancerController.roleArn')"
route53_hosted_zone_id="$(json_get '.dns_contract.value.route53_hosted_zone_id')"
ingress_domain_name="$(json_get '.dns_contract.value.ingress_domain_name')"
observability_domain_name="$(json_get '.dns_contract.value.observability_domain_name')"
external_dns_sa_name="$(json_get '.controllers.value.external_dns.service_account_name')"
awslbc_sa_name="$(json_get '.controllers.value.aws_load_balancer_controller.service_account_name')"

cluster_name="${HELM_AWSLBC_CLUSTER_NAME:-$(json_get '.eks.value.cluster_name')}"
if [ -z "${cluster_name}" ]; then
  echo "HELM_AWSLBC_CLUSTER_NAME is required (or Terraform must export eks.cluster_name)." >&2
  exit 1
fi

if [ -z "${aws_region}" ] || [ -z "${vpc_id}" ]; then
  echo "missing required Terraform outputs: helm_values.global.awsRegion or network.vpc_id" >&2
  exit 1
fi

if [ -z "${external_dns_role_arn}" ] || [ -z "${awslbc_role_arn}" ]; then
  echo "missing controller role ARNs; enable/verify Terraform controllers outputs" >&2
  exit 1
fi

if [ -z "${route53_hosted_zone_id}" ]; then
  echo "missing dns_contract.route53_hosted_zone_id in Terraform outputs" >&2
  exit 1
fi

owner_id="${HELM_EXTERNALDNS_TXT_OWNER_ID:-${TF_ENV:-dev}}"
if [ -z "${owner_id}" ]; then
  owner_id="opscopilot"
fi

{
  echo "serviceAccount:"
  echo "  create: true"
  if [ -n "${external_dns_sa_name}" ]; then
    echo "  name: ${external_dns_sa_name}"
  else
    echo "  name: external-dns"
  fi
  echo "  annotations:"
  echo "    eks.amazonaws.com/role-arn: \"${external_dns_role_arn}\""
  echo
  echo "provider:"
  echo "  name: aws"
  echo "  domainFilters:"
  if [ -n "${ingress_domain_name}" ]; then
    echo "    - \"${ingress_domain_name}\""
  fi
  if [ -n "${observability_domain_name}" ]; then
    echo "    - \"${observability_domain_name}\""
  fi
  echo "  zoneType: public"
  echo
  echo "registry:"
  echo "  type: txt"
  echo "  txtOwnerId: \"${owner_id}\""
  echo "  txtPrefix: \"external-dns-\""
  echo
  echo "policy: upsert-only"
  echo "interval: \"1m\""
  echo "logLevel: info"
  echo "logFormat: json"
  echo
  echo "terraform:"
  echo "  outputContractVersion: \"v1\""
  echo "  dnsContract:"
  echo "    route53_hosted_zone_id: \"${route53_hosted_zone_id}\""
} >"${external_dns_out}"

{
  echo "clusterName: \"${cluster_name}\""
  echo "region: \"${aws_region}\""
  echo "vpcId: \"${vpc_id}\""
  echo
  echo "serviceAccount:"
  echo "  create: true"
  if [ -n "${awslbc_sa_name}" ]; then
    echo "  name: ${awslbc_sa_name}"
  else
    echo "  name: aws-load-balancer-controller"
  fi
  echo "  annotations:"
  echo "    eks.amazonaws.com/role-arn: \"${awslbc_role_arn}\""
  echo
  echo "ingressClass: alb"
  echo
  echo "enableShield: false"
  echo "enableWaf: false"
  echo "enableWafv2: false"
  echo
  echo "logLevel: info"
  echo
  echo "resources: {}"
} >"${awslbc_out}"

echo "generated ${external_dns_out}"
echo "generated ${awslbc_out}"
