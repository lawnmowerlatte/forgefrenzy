data aws_caller_identity current {}

locals {
  prefix = "gateway"
  account_id          = data.aws_caller_identity.current.account_id
  ecr_repository_name = "${local.prefix}-forgefrenzy-lambda-container"
  ecr_image_tag       = "latest"
}

resource aws_ecr_repository repo {
  name = local.ecr_repository_name
}

data "archive_file" "init" {
  type        = "zip"
  source_dir = "../src/forgefrenzy/"
  output_path = "forgefrenzy.zip"
}

resource null_resource ecr_image {
  triggers = {
    python_sha = data.archive_file.init.output_sha
    docker_file = md5(file("${path.module}/../docker/lambda/Dockerfile"))
  }

  provisioner "local-exec" {
    command = <<EOF
      aws ecr get-login-password --region ${var.region} \
        | docker login \
            --username AWS \
            --password-stdin \
            ${local.account_id}.dkr.ecr.${var.region}.amazonaws.com
      cd ${path.module}/../
      docker build \
        -f docker/lambda/Dockerfile \
        --target handler \
        -t ${aws_ecr_repository.repo.repository_url}:${local.ecr_image_tag} .
      docker push \
        ${aws_ecr_repository.repo.repository_url}:${local.ecr_image_tag}
    EOF
  }
}

data aws_ecr_image lambda_image {
  depends_on = [
    null_resource.ecr_image
  ]
  repository_name = local.ecr_repository_name
  image_tag       = local.ecr_image_tag
}

resource aws_iam_role lambda {
  name = "${local.prefix}-lambda-role"
  assume_role_policy = <<EOF
{
   "Version": "2012-10-17",
   "Statement": [
       {
           "Action": "sts:AssumeRole",
           "Principal": {
               "Service": "lambda.amazonaws.com"
           },
           "Effect": "Allow"
       }
   ]
}
 EOF
}

data aws_iam_policy_document lambda {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    effect = "Allow"
    resources = [ "*" ]
    sid = "CreateCloudWatchLogs"
  }

  statement {
    actions = [
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:CreateTable",
      "dynamodb:GetItem",
      "dynamodb:GetRecords",
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:UpdateItem",
      "dynamodb:UpdateTable"
    ]
    effect = "Allow"
    resources = [ "*" ]
    sid = "DynamoDB"
  }
}

resource aws_iam_policy lambda {
  name = "${local.prefix}-lambda-policy"
  path = "/"
  policy = data.aws_iam_policy_document.lambda.json
}

resource aws_lambda_function gateway {
  depends_on = [
    null_resource.ecr_image
  ]
  function_name = "${local.prefix}-lambda"
  role = aws_iam_role.lambda.arn
  timeout = 300
  image_uri = "${aws_ecr_repository.repo.repository_url}@${data.aws_ecr_image.lambda_image.id}"
  package_type = "Image"
}

output "lambda_name" {
  value = aws_lambda_function.gateway.id
}

#### Admin Lambda ####

resource aws_ecr_repository admin_repo {
  name = "admin-${local.ecr_repository_name}"
}

resource null_resource admin_ecr_image {
  triggers = {
    python_sha = data.archive_file.init.output_sha
    docker_file = md5(file("${path.module}/../docker/lambda/Dockerfile"))
  }

  provisioner "local-exec" {
    command = <<EOF
                  aws ecr get-login-password --region ${var.region} \
        | docker login \
            --username AWS \
            --password-stdin \
            ${local.account_id}.dkr.ecr.${var.region}.amazonaws.com
      cd ${path.module}/../
      docker build \
        -f docker/lambda/Dockerfile \
        --target admin \
        -t ${aws_ecr_repository.admin_repo.repository_url}:${local.ecr_image_tag} .
      docker push \
        ${aws_ecr_repository.admin_repo.repository_url}:${local.ecr_image_tag}
    EOF
  }
}

data aws_ecr_image admin_lambda_image {
  depends_on = [
    null_resource.admin_ecr_image
  ]
  repository_name = "admin-${local.ecr_repository_name}"
  image_tag       = local.ecr_image_tag
}

data aws_iam_policy_document admin_lambda {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    effect = "Allow"
    resources = [ "*" ]
    sid = "CreateCloudWatchLogs"
  }

  statement {
    actions = [
      "dynamodb:*"
    ]
    effect = "Allow"
    resources = [ "*" ]
    sid = "DynamoDB"
  }
}

resource aws_iam_policy admin_lambda {
  name = "${local.prefix}-admin_lambda-policy"
  path = "/"
  policy = data.aws_iam_policy_document.admin_lambda.json
}

resource aws_lambda_function admin_gateway {
  depends_on = [
    null_resource.admin_ecr_image
  ]
  function_name = "admin-${local.prefix}-lambda"
  role = aws_iam_role.lambda.arn
  timeout = 300
  image_uri = "${aws_ecr_repository.admin_repo.repository_url}@${data.aws_ecr_image.admin_lambda_image.id}"
  package_type = "Image"
}

output "admin_lambda_name" {
  value = aws_lambda_function.admin_gateway.id
}
