variable "alert_email" {
  description = "Address that receives the budget alerts. Set it in terraform.tfvars, which git ignores."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must look like an email address."
  }
}
