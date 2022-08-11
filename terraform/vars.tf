#module "api-gateway-lambda-dynamodb" {
#  source  = "crisboarna/api-gateway-lambda-dynamodb/aws"
#  version = "1.16.0"
#
#  # General
#  owner = "lawnmowerlatte"
#  project = "forgefrenzy"
#  description = "API Gateway for Dwarven Forge data proxy"
#
#
#  #Global
#  region = "us-east-1"
#
#  #API Gateway
#  api_gw_method = "GET"
#
#  #Lambda
#  lambda_function_name = "${project}-api-gw"
#  lambda_description = description
#  lambda_runtime = "python3.9"
#  lambda_handler = "dist/bin/lambda.handler"
#  lambda_timeout = 30
#  lambda_code_s3_bucket = lambda_function_name
#  lambda_code_s3_key = "${lambda_function_name}.zip"
#  lambda_code_s3_storage_class = "ONEZONE_IA"
#  lambda_code_s3_bucket_visibility = "private"
#  lambda_zip_path = "../../${lambda_function_name}.zip"
#  lambda_memory_size = 256
#  lambda_vpc_security_group_ids = [aws_security_group.vpc_security_group.id]
#  lambda_vpc_subnet_ids = [aws_subnet.vpc_subnet_a.id]
#  lambda_layers = [data.aws_lambda_layer_version.layer.arn]
#
#  #DynamoDB
#  dynamodb_table_properties = [
#    {
#      name = "product",
#      read_capacity = 2,
#      write_capacity = 3,
#      hash_key = "KEY"
#      range_key = ""
#      stream_enabled = "true"
#      stream_view_type = "NEW_IMAGE"
#    },
#    {
#      name = "set",
#      read_capacity = 2,
#      write_capacity = 3,
#      hash_key = "KEY"
#      range_key = ""
#      stream_enabled = "true"
#      stream_view_type = "NEW_IMAGE"
#    },
#    {
#      name = "piece",
#      read_capacity = 2,
#      write_capacity = 3,
#      hash_key = "KEY"
#      range_key = ""
#      stream_enabled = "true"
#      stream_view_type = "NEW_IMAGE"
#    },
#    {
#      name = "partlist",
#      read_capacity = 2,
#      write_capacity = 3,
#      hash_key = "KEY"
#      range_key = ""
#      stream_enabled = "true"
#      stream_view_type = "NEW_IMAGE"
#    }
#  ]
#
#  dynamodb_table_attributes = [[
#    {
#      name = "KEY"
#      type = "S"
#    }],[
#    {
#      name = "PRIMARY_KEY"
#      type = "N"
#    }, {
#      name = "SECONDARY_KEY"
#      type = "S"
#    }
#  ]]
#
#  dynamodb_table_secondary_index = [[
#    {
#      name               = "GameTitleIndex"
#      hash_key           = "GameTitle"
#      range_key          = "TopScore"
#      write_capacity     = 10
#      read_capacity      = 10
#      projection_type    = "INCLUDE"
#      non_key_attributes = ["UserId"]
#    }
#  ]]
#
#  dynamodb_policy_action_list = [
#    "dynamodb:PutItem",
#    "dynamodb:DescribeTable",
#    "dynamodb:DeleteItem",
#    "dynamodb:GetItem",
#    "dynamodb:Scan",
#    "dynamodb:Query"
#  ]
#
#  #Tags
#  tags = {
#    owner = owner
#    project = project
#    managedby = "Terraform"
#  }
#
#  #Lambda Environment variables
#  environment_variables = {
#    NODE_ENV = "production"
#  }
#
#}
