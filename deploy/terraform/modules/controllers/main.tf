locals {
  enabled          = var.create && var.oidc_provider_arn != "" && var.oidc_provider_url != ""
  oidc_provider_id = replace(var.oidc_provider_url, "https://", "")

  external_dns_role_name = "${var.name_prefix}-external-dns"
  awslbc_role_name       = "${var.name_prefix}-aws-lb-controller"
}

data "aws_iam_policy_document" "external_dns_assume_role" {
  count = local.enabled ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_id}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_id}:sub"
      values = [
        "system:serviceaccount:${var.external_dns_namespace}:${var.external_dns_service_account_name}",
      ]
    }
  }
}

data "aws_iam_policy_document" "awslbc_assume_role" {
  count = local.enabled ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_id}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_id}:sub"
      values = [
        "system:serviceaccount:${var.aws_load_balancer_controller_namespace}:${var.aws_load_balancer_controller_service_account_name}",
      ]
    }
  }
}

data "aws_iam_policy_document" "external_dns_permissions" {
  count = local.enabled ? 1 : 0

  statement {
    sid = "ExternalDNSChangeRecordSets"
    actions = [
      "route53:ChangeResourceRecordSets",
    ]
    resources = ["arn:aws:route53:::hostedzone/*"]
  }

  statement {
    sid = "ExternalDNSReadRoute53"
    actions = [
      "route53:ListHostedZones",
      "route53:ListHostedZonesByName",
      "route53:ListResourceRecordSets",
      "route53:ListTagsForResource",
      "route53:GetHostedZone",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "awslbc_permissions" {
  count = local.enabled ? 1 : 0

  statement {
    sid = "ELBFullAccessForController"
    actions = [
      "elasticloadbalancing:*",
    ]
    resources = ["*"]
  }

  statement {
    sid = "EC2DescribeAndTagForController"
    actions = [
      "ec2:Describe*",
      "ec2:CreateSecurityGroup",
      "ec2:CreateTags",
      "ec2:DeleteTags",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:DeleteSecurityGroup",
      "ec2:ModifyInstanceAttribute",
      "ec2:ModifyNetworkInterfaceAttribute",
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:AssignPrivateIpAddresses",
      "ec2:UnassignPrivateIpAddresses",
      "ec2:GetCoipPoolUsage",
      "ec2:DescribeCoipPools",
    ]
    resources = ["*"]
  }

  statement {
    sid = "IAMServerCertificateRead"
    actions = [
      "iam:ListServerCertificates",
      "iam:GetServerCertificate",
      "iam:CreateServiceLinkedRole",
    ]
    resources = ["*"]
  }

  statement {
    sid = "WAFAndShieldRead"
    actions = [
      "waf-regional:GetWebACL",
      "waf-regional:GetWebACLForResource",
      "waf-regional:AssociateWebACL",
      "waf-regional:DisassociateWebACL",
      "wafv2:GetWebACL",
      "wafv2:GetWebACLForResource",
      "wafv2:AssociateWebACL",
      "wafv2:DisassociateWebACL",
      "shield:GetSubscriptionState",
      "shield:DescribeProtection",
      "shield:CreateProtection",
      "shield:DeleteProtection",
      "cognito-idp:DescribeUserPoolClient",
      "acm:ListCertificates",
      "acm:DescribeCertificate",
      "tag:GetResources",
      "tag:TagResources",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "external_dns" {
  count       = local.enabled ? 1 : 0
  name        = "${local.external_dns_role_name}-policy"
  description = "Permissions for ExternalDNS to manage Route53 records"
  policy      = data.aws_iam_policy_document.external_dns_permissions[0].json
  tags        = var.tags
}

resource "aws_iam_policy" "awslbc" {
  count       = local.enabled ? 1 : 0
  name        = "${local.awslbc_role_name}-policy"
  description = "Permissions for AWS Load Balancer Controller"
  policy      = data.aws_iam_policy_document.awslbc_permissions[0].json
  tags        = var.tags
}

resource "aws_iam_role" "external_dns" {
  count              = local.enabled ? 1 : 0
  name               = local.external_dns_role_name
  assume_role_policy = data.aws_iam_policy_document.external_dns_assume_role[0].json
  tags               = var.tags
}

resource "aws_iam_role" "awslbc" {
  count              = local.enabled ? 1 : 0
  name               = local.awslbc_role_name
  assume_role_policy = data.aws_iam_policy_document.awslbc_assume_role[0].json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "external_dns" {
  count      = local.enabled ? 1 : 0
  role       = aws_iam_role.external_dns[0].name
  policy_arn = aws_iam_policy.external_dns[0].arn
}

resource "aws_iam_role_policy_attachment" "awslbc" {
  count      = local.enabled ? 1 : 0
  role       = aws_iam_role.awslbc[0].name
  policy_arn = aws_iam_policy.awslbc[0].arn
}
