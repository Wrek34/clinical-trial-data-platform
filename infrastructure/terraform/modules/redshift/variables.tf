# Redshift Module Variables

variable "name_prefix" {
  type = string
}

variable "environment" {
  type = string
}

variable "redshift_role_arn" {
  type = string
}

variable "base_capacity" {
  type    = number
  default = 8
}

variable "max_capacity" {
  type    = number
  default = 64
}

variable "data_bucket_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
