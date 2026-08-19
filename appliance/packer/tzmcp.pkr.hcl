packer {
  required_plugins {
    virtualbox = {
      source  = "github.com/hashicorp/virtualbox"
      version = ">= 1.0.0"
    }
  }
}

source "virtualbox-iso" "tzmcp" {
  iso_url       = var.iso_url
  iso_checksum  = "sha256:${var.iso_sha256}"
  vm_name       = var.vm_name
  guest_os_type = "Ubuntu_64"
  cpus          = 2
  memory        = 4096
  disk_size     = 61440
  headless      = false
  http_content = {
    "/user-data" = templatefile(abspath("${path.root}/ubuntu/http/user-data"), {
      build_username      = var.build_username
      build_password_hash = var.build_password_hash
    })
    "/meta-data" = file(abspath("${path.root}/ubuntu/http/meta-data"))
  }
  boot_wait              = "10s"
  boot_keygroup_interval = "500ms"
  boot_command           = ["<esc><wait>", "e<wait>", "<down><down><down><end><wait>", " autoinstall cloud-config-url=/dev/null ds=nocloud-net\\;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/<wait>", "<f10>"]
  ssh_username           = var.build_username
  ssh_password           = var.build_password
  ssh_timeout            = "30m"
  shutdown_command       = "echo '${var.build_password}' | sudo -S shutdown -P now"

  vboxmanage = [
    ["modifyvm", "{{.Name}}", "--cpus", "2"],
    ["modifyvm", "{{.Name}}", "--memory", "4096"],
    ["modifyvm", "{{.Name}}", "--vram", "128"],
    ["modifyvm", "{{.Name}}", "--clipboard-mode", "disabled"],
    ["modifyvm", "{{.Name}}", "--drag-and-drop", "disabled"],
    ["modifyvm", "{{.Name}}", "--usb", "off"],
    ["modifyvm", "{{.Name}}", "--nic1", "nat"],
  ]
}

build {
  sources = ["source.virtualbox-iso.tzmcp"]

  provisioner "shell" {
    script          = abspath("${path.root}/../provisioning/install-base.sh")
    execute_command = "echo '${var.build_password}' | sudo -S -E sh '{{ .Path }}'"
  }

  provisioner "file" {
    source      = abspath(var.tzmcp_wheel)
    destination = "/tmp/"
  }

  provisioner "file" {
    source      = abspath("${path.root}/../files/tzmcp-first-boot.service")
    destination = "/tmp/tzmcp-first-boot.service"
  }

  provisioner "file" {
    source      = abspath("${path.root}/../files/tzmcp.desktop")
    destination = "/tmp/tzmcp.desktop"
  }

  provisioner "file" {
    source      = abspath("${path.root}/../files/tzmcp-export-helper")
    destination = "/tmp/tzmcp-export-helper"
  }

  provisioner "file" {
    source      = abspath("${path.root}/../provisioning/first-boot.sh")
    destination = "/tmp/tzmcp-first-boot"
  }

  provisioner "shell" {
    script          = abspath("${path.root}/../provisioning/install-tzmcp.sh")
    execute_command = "echo '${var.build_password}' | sudo -S -E sh '{{ .Path }}'"
  }

  provisioner "shell" {
    scripts         = [abspath("${path.root}/../provisioning/configure-desktop.sh"), abspath("${path.root}/../provisioning/install-export-helper.sh"), abspath("${path.root}/../provisioning/configure-security.sh"), abspath("${path.root}/../provisioning/scrub-image.sh")]
    execute_command = "echo '${var.build_password}' | sudo -S -E sh '{{ .Path }}'"
  }

  post-processor "manifest" {
    output     = abspath("${path.root}/../../dist/appliance-manifest.json")
    strip_path = true
  }
}
