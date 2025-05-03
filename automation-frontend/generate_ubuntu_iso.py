import os
import yaml
import shutil
import subprocess
from pathlib import Path

# === PATH SETUP ===
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
MOD_DIR = os.path.expanduser("~/ubuntu-iso-mod")
ORIG_GRUB = os.path.join(MOD_DIR, "boot/grub/grub.cfg")
VARS_PATH = os.path.join(BASE_DIR, "vars.yaml")
USER_TEMPLATE = os.path.join(TEMPLATE_DIR, "user-data-template.yaml")
META_TEMPLATE = os.path.join(TEMPLATE_DIR, "meta-data-template")
OUTPUT_ISO = os.path.join(BASE_DIR, "ubuntu-autoinstall.iso")

# === LOAD FORM INPUTS ===
def load_vars():
    with open(VARS_PATH, 'r') as f:
        return yaml.safe_load(f)

# === INJECT CLOUD-INIT FILES ===
def inject_cloud_init(vars_data):
    ubuntu_dir = os.path.join(MOD_DIR, "ubuntu")
    os.makedirs(ubuntu_dir, exist_ok=True)

    with open(USER_TEMPLATE, 'r') as f:
        user_template = f.read()
    with open(META_TEMPLATE, 'r') as f:
        meta_template = f.read()

    for key, value in vars_data.items():
        user_template = user_template.replace(f"{{{{ {key} }}}}", str(value))
        meta_template = meta_template.replace(f"{{{{ {key} }}}}", str(value))

    with open(os.path.join(ubuntu_dir, "user-data"), 'w') as f:
        f.write(user_template)

    with open(os.path.join(ubuntu_dir, "meta-data"), 'w') as f:
        f.write(meta_template)

# === MODIFY GRUB CONFIG TO BOOT WITH AUTOINSTALL ===
def update_grub():
    with open(ORIG_GRUB, 'r') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith("linux") and "autoinstall" not in line:
            # Add cloud-init seedfrom
            line = line.replace(
                " ---",
                " autoinstall quiet ---"
            )
        new_lines.append(line)

    with open(ORIG_GRUB, 'w') as f:
        f.writelines(new_lines)

# === REBUILD ISO ===
def build_iso(vm_name):
    output_dir = os.path.expanduser("~/ubuntu-iso-new")
    os.makedirs(output_dir, exist_ok=True)
    output_iso = os.path.join(output_dir, f"{vm_name}_ubuntu.iso")

    subprocess.run([
        "xorriso", "-as", "mkisofs",
        "-r", "-V", "cidata",
        "-o", output_iso,
        "-J", "-joliet-long", "-l", "-cache-inodes",
        "-isohybrid-mbr", "/usr/lib/ISOLINUX/isohdpfx.bin",
        "-eltorito-boot", "isolinux/isolinux.bin",
        "-boot-load-size", "4", "-boot-info-table", "--no-emul-boot",
        "-eltorito-alt-boot",
        "-e", "EFI/BOOT/BOOTx64.EFI",
        "-no-emul-boot",
        MOD_DIR
    ], check=True)

    print(f"Final ISO created at: {output_iso}")

# === MAIN FUNCTION ===
def generate_iso():
    vars_data = load_vars()
    inject_cloud_init(vars_data)
    update_grub()
    build_iso(vars_data["vm_name"])

if __name__ == "__main__":
    generate_iso()

