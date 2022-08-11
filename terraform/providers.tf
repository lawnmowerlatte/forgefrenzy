provider "aws" {
  region                  = "us-east-1"
  shared_credentials_file = "~/.aws/credentials"
#  profile                 = "lawnmowerlatte"
  default_tags {
      tags = {
          owner = "lawnmowerlatte"
          project = "forgefrenzy"
          managed_by = "terraform"
      }
  }

}

terraform {
  backend "s3" {
    bucket = "forgefrenzy-terraform"
    key    = "lambda.tfstate"
    region = "us-east-1"
  }
}
