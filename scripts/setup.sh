#!/bin/bash

# Azure DevOps to GitHub Migration Tool Setup Script
# This script creates a virtual environment (if not present), installs the
# package in editable mode (pip install -e .) and prepares baseline config
# files and sample artifacts for usage. It also validates the CLI.

set -e  # Exit on any error

echo "🚀 Setting up Azure DevOps to GitHub Migration Tool..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3 is installed
check_python() {
    print_status "Checking Python installation..."
    
    # Try python3 first, then python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    elif command -v python &> /dev/null && python --version 2>&1 | grep -q "Python 3"; then
        PYTHON_CMD="python"
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
    else
        print_error "Python 3.8+ is required but not found. Please install Python 3.8 or higher."
        print_error "Download from: https://www.python.org/downloads/"
        exit 1
    fi
    
    # Check version is 3.8+
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        print_success "Python $PYTHON_VERSION found ($PYTHON_CMD)"
    else
        print_error "Python 3.8+ is required. Found version $PYTHON_VERSION"
        print_error "Please upgrade Python: https://www.python.org/downloads/"
        exit 1
    fi
}

# Check if pip is installed
check_pip() {
    print_status "Checking pip installation..."
    if command -v pip3 &> /dev/null; then
        print_success "pip3 found"
    elif command -v pip &> /dev/null; then
        print_success "pip found"
        alias pip3=pip
    else
        print_error "pip is required but not installed. Please install pip."
        exit 1
    fi
}

# Create virtual environment
create_venv() {
    print_status "Ensuring virtual environment exists (./venv)..."
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv || {
            print_error "Failed to create virtual environment"
            exit 1
        }
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists (reuse)"
    fi
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    # shellcheck disable=SC1091
    if [ -f "venv/bin/activate" ]; then
        # Unix / WSL / Git Bash
        # shellcheck disable=SC1091
        . venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        # Git Bash on Windows may still source this
        # shellcheck disable=SC1091
        . venv/Scripts/activate
    else
        print_error "Could not locate activation script."
        exit 1
    fi
    print_success "Virtual environment activated (python: $(python -V 2>/dev/null))"
}

# Install dependencies
install_package() {
    print_status "Installing project in editable mode..."
    pip install --upgrade pip >/dev/null 2>&1 || print_warning "Pip upgrade failed (continuing)"
    if [ -n "${SETUP_DEV:-}" ]; then
        print_status "Installing with development extras..."
        pip install -e .[dev]
    else
        pip install -e .
    fi
    print_success "Editable install complete"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p migration_reports
    mkdir -p logs
    mkdir -p temp
    print_success "Directories created"
}

# Copy configuration template
setup_config() {
    print_status "Setting up configuration files..."
    mkdir -p config
    if [ -f "config/config.template.json" ] && [ ! -f "config/config.json" ]; then
        cp config/config.template.json config/config.json
        print_success "Copied config/config.template.json -> config/config.json"
        print_warning "Edit config/config.json with your Azure DevOps and GitHub settings"
    elif [ -f "config/config.json" ]; then
        print_warning "config/config.json already exists (leaving untouched)"
    else
        print_warning "config/config.template.json not found (skipping)"
    fi

    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        cp .env.example .env
        print_success "Copied .env.example -> .env"
        print_warning "Edit .env with required tokens (AZURE_DEVOPS_PAT / GITHUB_TOKEN)"
    fi
}

# Check Git installation
check_git() {
    print_status "Checking Git installation..."
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version | cut -d' ' -f3)
        print_success "Git $GIT_VERSION found"
    else
        print_error "Git is required but not installed. Please install Git."
        exit 1
    fi
}

# Validate installation
validate_installation() {
    print_status "Validating CLI installation..."
    if azuredevops-github-migration --version >/dev/null 2>&1; then
        print_success "CLI responds: $(azuredevops-github-migration --version)"
    else
        print_error "CLI did not execute correctly. Check installation output above."
        exit 1
    fi
}

# Generate sample migration plan
generate_sample_plan() {
    print_status "Generating sample migration plan..."
    
    cat > sample_migration_plan.json << EOF
{
  "migrations": [
    {
      "azure_devops": {
        "project": "YourProjectName",
        "repository": "your-repo-name"
      },
      "github": {
        "repository": "migrated-repo-name",
        "organization": "your-github-org"
      },
      "options": {
        "migrate_work_items": true,
        "migrate_branches": true,
        "create_private": true
      }
    }
  ]
}
EOF
    
    print_success "Sample migration plan created: sample_migration_plan.json"
}

# Create launcher scripts
create_launchers() {
    print_status "Creating convenience launcher scripts (wrapping CLI)..."

    cat > migrate << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -f "venv/bin/activate" ]; then . venv/bin/activate; elif [ -f "venv/Scripts/activate" ]; then . venv/Scripts/activate; fi
azuredevops-github-migration migrate "$@"
EOF
    chmod +x migrate || true

    cat > migrate.bat << 'EOF'
@echo off
cd /d "%~dp0"
IF EXIST venv\Scripts\activate.bat call venv\Scripts\activate.bat
azuredevops-github-migration migrate %*
EOF

    print_success "Launcher scripts created (migrate / migrate.bat)"
}

# Display next steps
show_next_steps() {
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "📝 Next Steps:"
    echo "1. Edit config/config.json with Azure DevOps + GitHub settings"
    echo "2. Provide tokens via environment (export) or .env if supported by your shell wrapper"
    echo "3. Explore commands:"
    echo "   azuredevops-github-migration help"
    echo "   azuredevops-github-migration analyze --create-plan --config config/config.json"
    echo "   azuredevops-github-migration migrate --project 'MyProject' --repo 'MyRepo' --config config/config.json"
    echo "   azuredevops-github-migration batch --plan sample_migration_plan.json --config config/config.json"
    echo ""
    echo "🔧 Development mode (you used [dev] extras if --dev): run pytest, flake8, mypy, etc."
    echo ""
    echo "📚 Documentation: README.md, docs/user-guide/HOW_TO_GUIDE.md"
    echo ""
    print_success "Happy migrating! 🚀"
}

# Main setup process
main() {
    echo "======================================"
    echo " Azure DevOps to GitHub Migration Tool"
    echo "======================================"
    echo ""
    
    check_python
    check_pip
    check_git
    create_venv
    activate_venv
    install_package
    create_directories
    setup_config
    validate_installation
    generate_sample_plan
    create_launchers
    show_next_steps
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Azure DevOps to GitHub Migration Tool Setup"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --clean        Clean previous installation"
        echo "  --dev          Setup for development (installs dev dependencies)"
        echo ""
        exit 0
        ;;
    --clean)
        print_status "Cleaning previous installation..."
        rm -rf venv migration_reports logs temp
        rm -f config.json .env migrate migrate.bat
        print_success "Cleanup completed"
        ;;
    --dev)
        print_status "Setting up development environment..."
        export SETUP_DEV=1
        ;;
esac

# Run main setup
main