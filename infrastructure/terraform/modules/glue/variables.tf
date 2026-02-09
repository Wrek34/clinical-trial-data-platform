# Glue Module Variables

variable "name_prefix" {
  type = string
}

variable "environment" {
  type = string
}

variable "glue_role_arn" {
  type = string
}

variable "data_bucket_name" {
  type = string
}

variable "scripts_bucket" {
  type = string
}

variable "glue_version" {
  type    = string
  default = "4.0"
}

variable "worker_type" {
  type    = string
  default = "G.1X"
}

variable "number_of_workers" {
  type    = number
  default = 2
}

variable "tags" {
  type    = map(string)
  default = {}
}
