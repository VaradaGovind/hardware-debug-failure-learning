#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Setup script for Ubuntu / WSL environment
# 1. Creates rca_workspace/
# 2. Ensures rca_workspace/ is appended to root .gitignore
# 3. Initializes and activates a Python virtual environment inside rca_workspace/
# 4. Installs PyTorch with ROCm 6.0 support and soup-cli[train]
# ==============================================================================

# Determine root repository directory
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "==> Repository Root: ${REPO_ROOT}"

# 1. Create workspace directory
echo "==> Creating 'rca_workspace' directory..."
mkdir -p rca_workspace

# 2. Append rca_workspace/ to root .gitignore if not already present
GITIGNORE_FILE="${REPO_ROOT}/.gitignore"
if [ ! -f "${GITIGNORE_FILE}" ] || ! grep -qxF "rca_workspace/" "${GITIGNORE_FILE}"; then
    echo "==> Appending 'rca_workspace/' to .gitignore..."
    echo "" >> "${GITIGNORE_FILE}"
    echo "# RCA Workspace" >> "${GITIGNORE_FILE}"
    echo "rca_workspace/" >> "${GITIGNORE_FILE}"
else
    echo "==> 'rca_workspace/' is already present in .gitignore."
fi

# 3. Enter rca_workspace and initialize virtual environment
cd "${REPO_ROOT}/rca_workspace"

echo "==> Initializing Python virtual environment (.venv)..."
python3 -m venv .venv

# 4. Activate virtual environment
echo "==> Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

# 5. Upgrade pip
echo "==> Upgrading pip..."
pip install --upgrade pip

# 6. Install PyTorch with ROCm 6.0 support
echo "==> Installing PyTorch with ROCm 6.0 support..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0

# 7. Install soup-cli[train]
echo "==> Installing soup-cli[train]..."
pip install "soup-cli[train]"

echo ""
echo "=============================================================================="
echo " Workspace setup complete!"
echo " To activate this environment in future sessions, run:"
echo "   source ${REPO_ROOT}/rca_workspace/.venv/bin/activate"
echo "=============================================================================="
