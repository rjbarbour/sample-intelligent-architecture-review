# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

###############################################################################
# Bedrock Module - IAM role and policy for Bedrock model invocation
###############################################################################

data "aws_caller_identity" "current" {}

###############################################################################
# IAM Policy for Bedrock Access
###############################################################################

data "aws_iam_policy_document" "bedrock_access" {
  statement {
    sid    = "AllowBedrockInvocation"
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:Converse",
      "bedrock:ConverseStream",
      "bedrock:GetInferenceProfile",
    ]

    resources = [
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
      "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
      "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/us.anthropic.*",
    ]
  }

  statement {
    sid    = "AllowBedrockModelListing"
    effect = "Allow"

    actions = [
      "bedrock:ListFoundationModels",
      "bedrock:GetFoundationModel",
    ]

    resources = ["*"]
  }

  statement {
    sid    = "AllowBedrockKnowledgeBase"
    effect = "Allow"

    actions = [
      "bedrock:Retrieve",
      "bedrock:RetrieveAndGenerate",
    ]

    resources = [
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*",
    ]
  }

  statement {
    sid    = "AllowBedrockAgentDataSource"
    effect = "Allow"

    actions = [
      "bedrock:StartIngestionJob",
      "bedrock:GetIngestionJob",
      "bedrock:ListIngestionJobs",
    ]

    resources = [
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*",
    ]
  }
}


###############################################################################
# Attach Bedrock Policy to ECS Task Role
###############################################################################
