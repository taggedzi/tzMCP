# Path: scripts/clean_unused_packages.py
# pylint: disable=line-too-long,broad-exception-caught
"""
Search a project and attempt to remove unused packages, accounting for dependencies,
using importlib.metadata; generate cleaned requirements and removal recommendations.
"""
import ast
import subprocess
import sys
import sysconfig
from pathlib import Path
import importlib.metadata as metadata


def get_installed_packages():
    """Get a set of all installed package distribution names (lowercased)."""
    return {dist.metadata['Name'].lower() for dist in metadata.distributions() if 'Name' in dist.metadata}


def get_imported_modules(code_root: Path):
    """Get a set of all top-level modules imported from code_root."""
    imported_loc = set()
    for file in code_root.rglob("*.py"):
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_loc.add(alias.name.split('.')[0].lower())
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_loc.add(node.module.split('.')[0].lower())
        except Exception as e:
            print(f"⚠️ Skipping {file}: {e}")
    return imported_loc


def stdlib_modules():
    """Return a set of standard library module names."""
    if hasattr(sys, 'stdlib_module_names'):
        return set(m.lower() for m in sys.stdlib_module_names)
    stdlib_path = sysconfig.get_paths()["stdlib"]
    return {p.name.lower() for p in Path(stdlib_path).iterdir() if p.is_dir()}


def get_all_dependencies(packages):
    """
    Given an iterable of distribution names, return a set of all recursive dependencies.
    """
    deps = set()
    to_process = list(packages)
    while to_process:
        pkg = to_process.pop()
        try:
            dist = metadata.distribution(pkg)
        except metadata.PackageNotFoundError:
            continue
        for req in dist.requires or []:
            # Extract distribution name
            name = req.split(';', 1)[0].split('[')[0].split(' ')[0].split('=')[0].lower()
            if name and name not in packages and name not in deps:
                deps.add(name)
                to_process.append(name)
    return deps


def find_unneeded_packages(imported_modules, installed_packages):
    """Find distributions installed but not needed by imports or dependencies."""
    builtin = stdlib_modules()
    # Map top-level modules to distributions
    pkg2dist = metadata.packages_distributions()
    # Identify distributions directly used by imports
    safe = set()
    for mod in imported_modules:
        if mod in builtin:
            continue
        for dist in pkg2dist.get(mod, []):
            safe.add(dist.lower())
    # Filter to installed distributions
    safe = safe & set(installed_packages)
    # Add recursive dependencies
    all_needed = set(safe)
    all_needed.update(get_all_dependencies(safe))
    # Unused = installed minus needed
    return sorted(installed_packages - all_needed)


def uninstall_packages(packages):
    """Uninstall the given list of packages via pip."""
    for pkg in packages:
        confirm = input(f"Uninstall '{pkg}'? [y/N]: ").strip().lower()
        if confirm == 'y':
            subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', pkg], check=False)


def write_recommendations(unused, rec_file: Path):
    """Write recommended removals to a text file."""
    rec_file.write_text('\n'.join(unused) + '\n', encoding='utf-8')
    print(f"📄 Recommended removals saved to: {rec_file}")


def write_clean_requirements(unused, req_file: Path):
    """Generate a cleaned requirements.txt and write to file."""
    try:
        freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
        lines = []
        for line in freeze.splitlines():
            name = line.split('==')[0].lower()
            if name not in unused:
                lines.append(line)
        req_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f"📄 Cleaned requirements saved to: {req_file}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate cleaned requirements: {e}")


def main():
    """Main function."""
    print("🔍 Scanning for unused packages...")
    code_root = Path('.')  # customize if needed

    installed = get_installed_packages()
    imported = get_imported_modules(code_root)
    unused = find_unneeded_packages(imported, installed)

    print(f"\n📦 Unused packages ({len(unused)}):")
    for pkg in unused:
        print(f"  - {pkg}")

    # Always write recommendations and cleaned requirements
    rec_file = Path('recommended_removals.txt')
    req_file = Path('requirements_cleaned.txt')
    write_recommendations(unused, rec_file)
    write_clean_requirements(unused, req_file)

    if unused and input("\n❓ Uninstall them now? [y/N]: ").strip().lower() == 'y':
        uninstall_packages(unused)

if __name__ == '__main__':
    main()
