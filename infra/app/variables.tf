# Which Let's Encrypt environment issues the instance's certificate.
# Staging has much higher rate limits, but clients don't trust its
# certificates: use it while testing, e.g.
# TF_VAR_acme_ca=staging scripts/infra-app.sh up
variable "acme_ca" {
  description = "Let's Encrypt environment: staging or production"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["staging", "production"], var.acme_ca)
    error_message = "acme_ca must be \"staging\" or \"production\"."
  }
}
