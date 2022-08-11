
resource "aws_dynamodb_table" "ff_products_table" {
  name = "ff-products-table"
  billing_mode = "PROVISIONED"
  read_capacity= "30"
  write_capacity= "30"
  attribute {
    name = "handle"
    type = "S"
  }
  hash_key = "handle"
}

resource "aws_dynamodb_table" "ff_sets_table" {
  name = "ff-sets-table"
  billing_mode = "PROVISIONED"
  read_capacity= "30"
  write_capacity= "30"
  attribute {
    name = "sku"
    type = "S"
  }
  hash_key = "sku"
}

resource "aws_dynamodb_table" "ff_pieces_table" {
  name = "ff-pieces-table"
  billing_mode = "PROVISIONED"
  read_capacity= "30"
  write_capacity= "30"
  attribute {
    name = "sku"
    type = "S"
  }
  hash_key = "sku"
}

resource "aws_dynamodb_table" "ff_partlist_table" {
  name = "ff-partlist-table"
  billing_mode = "PROVISIONED"
  read_capacity= "30"
  write_capacity= "30"
  attribute {
    name = "sku"
    type = "S"
  }
  hash_key = "sku"
}
