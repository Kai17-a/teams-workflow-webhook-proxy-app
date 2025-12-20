provider "aws" {
  region = "ap-northeast-1"
}

resource "aws_ssm_parameter" "example" {
  name  = "/teams/tech-blog-pr-notification-channel/workflow/webhook-url"
  type  = "String"
  value = ""
}
