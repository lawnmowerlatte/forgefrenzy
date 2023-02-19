resource "aws_api_gateway_rest_api" "api" {
name = "forgefrenzy"
description = "Proxy to handle requests to our API"
}

locals {
  fqdn = "forgefrenzy.lawnmowerlatte.com"
  path = "ff"

}

resource "aws_api_gateway_resource" "resource" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "method" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resource.id
  http_method   = "ANY"
  authorization = "NONE"
  request_parameters = {
    "method.request.path.proxy" = true
  }
}

resource "aws_api_gateway_integration" "integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.resource.id
  http_method = aws_api_gateway_method.method.http_method
  integration_http_method = "ANY"
  type                    = "HTTP_PROXY"
  uri                     = "https://${local.fqdn}/${local.path}/{proxy}"

  request_parameters =  {
    "integration.request.path.proxy" = "method.request.path.proxy"
  }
}

resource "aws_api_gateway_domain_name" "domain" {
  domain_name = local.fqdn
  certificate_name = "forgefrenzy-api-gw"
  certificate_body = file("${path.module}/certificates/public.pem")
  certificate_chain = file("${path.module}/certificates/chain.pem")
  certificate_private_key = file("${path.module}/certificates/private.pem")
}

resource "aws_api_gateway_base_path_mapping" "base_path_mapping" {
  api_id      = aws_api_gateway_rest_api.api.id
  domain_name = aws_api_gateway_domain_name.domain.domain_name
}