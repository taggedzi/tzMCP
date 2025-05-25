# Path: tasks.py
"""Tasks for invoking tasks using Invoke."""
import re
import shutil
import os
import toml
from pathlib import Path
import subprocess
from invoke import task
import tempfile

PYPROJECT_PATH = Path("pyproject.toml")
INIT_PATH = Path("src/tzMCP/__init__.py")


@task
def setup(c):
    """Install the project in editable mode with dev dependencies."""
    c.run("pip install -e .[dev]")

@task
def test(c):
    """Run tests using pytest."""
    c.run("pytest")

@task
def coverage(c):
    """Run tests with coverage report."""
    c.run("pytest --cov=tzMCP --cov-report=term-missing")

@task
def coverage_html(c):
    """Generate HTML coverage report."""
    c.run("pytest --cov=tzMCP --cov-report=html")
    print("Open htmlcov/index.html in your browser to view the report.")

@task
def build(c):
    """Build the distribution packages."""
    c.run("python -m build")

@task
def clean(c):
    """Remove build artifacts."""
    c.run("rm -rf dist/ build/ *.egg-info htmlcov .pytest_cache")

@task
def cleanpy(c):   # pylint: disable=unused-argument
    """Remove __pycache__ and coverage artifacts."""
    for root, dirs, _ in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    if os.path.exists(".coverage"):
        os.remove(".coverage")

@task
def freeze(c):
    """Generate requirements.txt from current environment (useful for lockfiles)."""
    c.run("pip freeze > requirements.txt")


def get_current_version() -> str:
    pyproject = toml.load(PYPROJECT_PATH)
    return pyproject["project"]["version"]

def update_version(new_version: str):
    pyproject = toml.load(PYPROJECT_PATH)
    pyproject["project"]["version"] = new_version
    PYPROJECT_PATH.write_text(toml.dumps(pyproject))

@task
def release(c, version, test=False):
    """
    Automate a full release:
    - Set version
    - Commit version bump
    - Tag commit
    - Build dist
    - Upload to PyPI (or TestPyPI)

    Usage: invoke release --version=0.2.5
    Optional: --test (use TestPyPI instead of PyPI)
    """
    # Validate version
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print("❌ Version must follow semantic versioning, e.g., 1.2.3")
        return

    current_version = get_current_version()
    if current_version == version:
        print(f"🔁 Version already set to {version}, continuing...")
    else:
        print(f"🔧 Updating version: {current_version} → {version}")
        update_version(version)
        update_dunder_version(version)
        c.run(f'git add pyproject.toml {INIT_PATH}')
        c.run(f'git commit -m "Bump version to {version}"')

    tag_name = f"v{version}"
    existing_tags = subprocess.run(["git", "tag"], capture_output=True, text=True).stdout.splitlines()
    if tag_name in existing_tags:
        print(f"❌ Tag {tag_name} already exists.")
        return

    print(f"🏷️ Tagging release {tag_name}")
    c.run(f'git tag -a {tag_name} -m "Release {tag_name}"')
    c.run('git push')
    c.run(f'git push origin {tag_name}')

    print("📦 Building package...")
    c.run("rm -rf dist build *.egg-info", warn=True)
    c.run("python -m build --no-isolation")

    print("🚀 Uploading to PyPI...")
    if test:
        c.run("twine upload --repository testpypi dist/*")
    else:
        c.run("twine upload dist/*")

    print(f"✅ Release {version} complete.")


def update_dunder_version(version: str):
    """Update __version__ = 'x.y.z' in __init__.py."""
    if not INIT_PATH.exists():
        print(f"⚠️ {INIT_PATH} not found — skipping __version__ update.")
        return

    lines = INIT_PATH.read_text().splitlines()
    new_lines = []
    updated = False
    for line in lines:
        if line.strip().startswith("__version__"):
            new_lines.append(f'__version__ = "{version}"')
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.insert(0, f'__version__ = "{version}"')

    INIT_PATH.write_text("\n".join(new_lines) + "\n")
    print(f"🔢 Updated __version__ in {INIT_PATH}")


@task(help={"root": "Project root to clean (defaults to tasks.py location)"})
def clean_pycache(c, root="."):
    """
    Recursively delete all __pycache__ folders and stray *.pyc files.

    Example:
        inv clean-pycache          # clean from project root
        inv clean-pycache --root=../otherproj
    """
    root_path = Path(root).resolve()
    if not root_path.exists():
        print(f"[clean-pycache] Path not found: {root_path}")
        return

    removed_dirs = 0
    removed_files = 0

    for p in root_path.rglob("*"):
        # Remove __pycache__ directories
        if p.is_dir() and p.name == "__pycache__":
            shutil.rmtree(p, ignore_errors=True)
            removed_dirs += 1
        # Remove loose .pyc files (if any are outside __pycache__)
        elif p.is_file() and p.suffix == ".pyc":
            p.unlink(missing_ok=True)
            removed_files += 1

    print(
        f"[clean-pycache] removed {removed_dirs} __pycache__ director"
        f"ies and {removed_files} stray *.pyc files under {root_path}"
    )
    
    
@task
def clean_browser_profiles(c):
    """
    Remove old temp proxy profiles for Firefox, Chrome, Edge, etc.
    """
    temp = Path(tempfile.gettempdir())
    removed = 0
    for folder in temp.iterdir():
        if folder.is_dir() and any(key in folder.name.lower() for key in ["proxy", "profile", "chrome", "firefox", "edge"]):
            try:
                shutil.rmtree(folder, ignore_errors=True)
                print(f"🧹 Removed: {folder}")
                removed += 1
            except Exception as e:
                print(f"⚠️ Failed to remove {folder}: {e}")
    if removed == 0:
        print("✅ No matching temp profile folders found.")
    else:
        print(f"✅ Finished cleanup: {removed} folder(s) removed.")