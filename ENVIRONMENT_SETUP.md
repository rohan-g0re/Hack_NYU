# Environment Setup Guide

**WHAT:** Complete guide for managing the conda environment for this project  
**WHY:** Ensure consistent development environment across team members and machines  
**HOW:** Use conda to create, activate, and manage the Python environment with all dependencies

## Quick Start

### Activating the Environment

After the environment has been created, activate it using:

```bash
conda activate hackathon
```

**WHAT:** Activates the conda environment named "hackathon"  
**WHY:** Ensures you're using the correct Python version and all installed packages  
**HOW:** Conda modifies your PATH to prioritize packages from this environment

### Deactivating the Environment

When you're done working, deactivate the environment:

```bash
conda deactivate
```

**WHAT:** Returns your shell to the base conda environment  
**WHY:** Prevents conflicts with other projects or system Python  
**HOW:** Restores your original PATH settings

## Environment Details

### Environment Name
- **Name:** `hackathon`
- **Python Version:** 3.10.19
- **Location:** `C:\Users\hackuser\Miniconda3\envs\hackathon` (or your conda installation path)

### Key Dependencies

**WHAT:** Core packages installed in this environment  
**WHY:** Provides the foundation for the multi-agent marketplace backend  
**HOW:** Managed through conda and pip

#### Conda Packages (Base System)
- Python 3.10.19
- NumPy 2.2.5 (with Intel MKL optimizations)
- SQLite 3.51.0
- Core system libraries (OpenSSL, zlib, etc.)

#### Pip Packages (Application Dependencies)
- **FastAPI/Web Framework:**
  - `anyio`, `httpx`, `httpcore` - Async HTTP client
  - `pydantic` - Data validation
  - `annotated-types` - Type annotations

- **LLM/ML Libraries:**
  - `torch` 2.9.0 - PyTorch for ML models
  - `torchvision` 0.24.0 - Computer vision utilities
  - `onnx`, `onnxruntime` - ONNX model support
  - `h5py` - HDF5 file format support

- **Utilities:**
  - `requests` - HTTP library
  - `colorama`, `coloredlogs` - Terminal output formatting
  - `tqdm` - Progress bars
  - `networkx` - Graph algorithms
  - `prettytable` - Formatted table output

## Creating the Environment (First Time Setup)

If you need to recreate the environment from scratch:

```bash
# Navigate to project root
cd Hack_NYU

# Create environment from YAML file
conda env create -f environment.yml

# Activate the environment
conda activate hackathon
```

**WHAT:** Creates a new conda environment matching the project specifications  
**WHY:** Ensures everyone has identical dependencies and versions  
**HOW:** Conda reads `environment.yml` and installs all listed packages

## Updating the Environment

If `environment.yml` has been updated:

```bash
# Activate environment first
conda activate hackathon

# Update environment from YAML
conda env update -f environment.yml --prune
```

**WHAT:** Updates existing environment to match the YAML file  
**WHY:** Keeps your environment in sync with project changes  
**HOW:** Conda adds new packages and removes ones no longer listed (--prune flag)

## Working with the Backend

### Setting Up Backend Dependencies

After activating the conda environment, install backend-specific dependencies:

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies (if using requirements.txt)
pip install -r requirements.txt

# OR if using Poetry (recommended)
poetry install
```

**WHAT:** Installs additional backend dependencies not in conda environment  
**WHY:** Backend may have its own dependency management (Poetry/requirements.txt)  
**HOW:** Pip/Poetry installs packages into the active conda environment

### Running the Backend

```bash
# Ensure environment is activated
conda activate hackathon

# Navigate to backend
cd backend

# Run the FastAPI server
python -m app.main

# OR with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**WHAT:** Starts the FastAPI backend server  
**WHY:** The conda environment provides all required Python packages  
**HOW:** Python uses packages from the activated conda environment

## Environment Variables

**WHAT:** Backend configuration stored in `.env` file  
**WHY:** Keeps sensitive data and configuration separate from code  
**HOW:** FastAPI reads environment variables on startup

1. Copy the template:
   ```bash
   cd backend
   cp env.template .env
   ```

2. Edit `.env` with your settings (see `backend/env.template` for details)

3. Key variables:
   - `LLM_PROVIDER=lm_studio` - Use local LM Studio
   - `LM_STUDIO_BASE_URL=http://localhost:1234/v1` - LM Studio endpoint
   - `DATABASE_URL=sqlite:///./data/marketplace.db` - Database location

## Common Workflows

### Daily Development Workflow

```bash
# 1. Activate environment
conda activate hackathon

# 2. Navigate to project
cd Hack_NYU/backend

# 3. Start backend server
python -m app.main

# 4. When done, deactivate
conda deactivate
```

### Adding New Dependencies

**WHAT:** Adding packages to the project  
**WHY:** New features may require additional libraries  
**HOW:** Update environment.yml and recreate environment

1. Install package in active environment:
   ```bash
   conda activate hackathon
   pip install new-package-name
   ```

2. Update `environment.yml`:
   ```bash
   conda env export > environment.yml
   ```
   (This exports current state - manually edit to keep it clean)

3. Or manually add to `environment.yml` under the `pip:` section

### Checking Installed Packages

```bash
# List all packages
conda list

# List only pip packages
pip list

# Check specific package
conda list numpy
```

## Troubleshooting

### Environment Not Found

**Problem:** `conda activate hackathon` fails with "Could not find conda environment"  
**Solution:**
```bash
# Recreate from YAML
conda env create -f environment.yml
```

### Package Import Errors

**Problem:** `ModuleNotFoundError` when running Python code  
**Solution:**
1. Verify environment is activated: `conda info --envs` (active one has `*`)
2. Check if package is installed: `pip list | grep package-name`
3. Reinstall if needed: `pip install package-name`

### Environment Location Issues

**Problem:** Environment created in wrong location  
**Solution:**
```bash
# Check current conda config
conda config --show envs_dirs

# Create environment in specific location
conda env create -f environment.yml -p /path/to/custom/location
```

### Windows ARM Compatibility

**WHAT:** Special considerations for Windows ARM laptops  
**WHY:** Some packages may not have ARM builds  
**HOW:** The environment.yml is configured for Windows ARM compatibility

- All packages in `environment.yml` are tested on Windows ARM
- PyTorch and ONNX Runtime have ARM-compatible builds
- If you encounter build errors, check package documentation for ARM support

### Conda vs Pip Conflicts

**Problem:** Packages installed via pip conflict with conda packages  
**Solution:**
- Prefer conda packages when available (faster, better dependency resolution)
- Use pip only for packages not available in conda
- The `environment.yml` already balances this correctly

## Exporting Environment

To share your environment with others or backup:

```bash
# Export full environment (includes all packages)
conda env export > environment.yml

# Export only explicitly installed packages (cleaner)
conda env export --from-history > environment.yml
```

**WHAT:** Creates a YAML file describing the environment  
**WHY:** Allows others to recreate your exact environment  
**HOW:** Conda exports package names and versions to YAML format

## Best Practices

1. **Always activate before working:**
   ```bash
   conda activate hackathon
   ```

2. **Keep environment.yml in version control:**
   - This ensures team consistency
   - Update it when adding major dependencies

3. **Use separate environments for different projects:**
   - Don't mix project dependencies
   - Each project should have its own conda environment

4. **Regular updates:**
   ```bash
   conda update --all  # Update conda packages
   pip list --outdated  # Check for pip package updates
   ```

5. **Clean up unused packages:**
   ```bash
   conda clean --all  # Remove cached packages
   ```

## Quick Reference

| Command | Description |
|---------|-------------|
| `conda activate hackathon` | Activate the environment |
| `conda deactivate` | Deactivate current environment |
| `conda env list` | List all environments |
| `conda info --envs` | Show environment locations |
| `conda list` | List packages in active environment |
| `conda env create -f environment.yml` | Create environment from file |
| `conda env update -f environment.yml` | Update environment from file |
| `conda env remove -n hackathon` | Delete the environment |

---

**Last Updated:** Based on environment created from `environment.yml`  
**Environment Name:** `hackathon`  
**Python Version:** 3.10.19

