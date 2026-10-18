variable "iso_url" {
  type    = string
  default = "https://releases.ubuntu.com/24.04/ubuntu-24.04.4-live-server-amd64.iso"
}

variable "iso_sha256" {
  type      = string
  sensitive = true
  default   = "e907d92eeec9df64163a7e454cbc8d7755e8ddc7ed42f99dbc80c40f1a138433"
}

variable "vm_name" {
  type    = string
  default = "tzMCP-appliance"
}

variable "appliance_version" {
  type    = string
  default = "development"
  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$", var.appliance_version))
    error_message = "Appliance version must be a 1-64 character release label using letters, digits, dot, underscore, plus, or hyphen."
  }
}

variable "build_username" {
  type    = string
  default = "tzmcp-build"
}

variable "build_password" {
  type      = string
  sensitive = true
}

variable "build_password_hash" {
  type      = string
  sensitive = true
}

variable "tzmcp_wheel" {
  type = string
}
