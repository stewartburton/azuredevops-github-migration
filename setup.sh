#!/bin/bash

# Azure DevOps to GitHub Migration Tool Setup Script
# This script sets up the migration tool environment

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
    print_status "Creating virtual environment..."
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        if [ $? -eq 0 ]; then
            print_success "Virtual environment created"
        else
            print_error "Failed to create virtual environment"
            print_error "Try: $PYTHON_CMD -m pip install --user virtualenv"
            exit 1
        fi
    else
        print_warning "Virtual environment already exists"
    fi
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
        print_success "Dependencies installed successfully"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
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
    
    if [ -f "config.template.json" ] && [ ! -f "config.json" ]; then
        cp config.template.json config.json
        print_success "Configuration template copied to config.json"
        print_warning "Please edit config.json with your Azure DevOps and GitHub credentials"
    elif [ -f "config.json" ]; then
        print_warning "config.json already exists, skipping template copy"
    else
        print_error "config.template.json not found"
    fi
    
    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        cp .env.example .env
        print_success "Environment template copied to .env"
        print_warning "Please edit .env with your personal access tokens"
    elif [ -f ".env" ]; then
        print_warning ".env already exists, skipping template copy"
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
    print_status "Validating installation..."
    
    # Test Python imports (use the activated environment)
    python -c "import requests, yaml, json, tqdm" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "Python dependencies validation passed"
    else
        print_error "Python dependencies validation failed"
        print_error "Run: pip install -r requirements.txt"
        exit 1
    fi
    
    # Check main script
    if [ -f "migrate.py" ]; then
        # Test the script can be imported
        python -c "import migrate" 2>/dev/null
        if [ $? -eq 0 ]; then
            print_success "Main migration script validated"
        else
            print_warning "Main migration script has import issues (may be normal)"
        fi
    else
        print_error "migrate.py not found"
        exit 1
    fi
    
    # Test configuration validation
    if [ -f "config.template.json" ]; then
        python -c "import json; json.load(open('config.template.json'))" 2>/dev/null
        if [ $? -eq 0 ]; then
            print_success "Configuration template is valid JSON"
        else
            print_error "Configuration template has JSON syntax errors"
        fi
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
    print_status "Creating launcher scripts..."
    
    # Unix/Linux launcher
    cat > migrate << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
python migrate.py "$@"
EOF
    chmod +x migrate
    
    # Batch launcher for Windows
    cat > migrate.bat << 'EOF'
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python migrate.py %*
EOF
    
    print_success "Launcher scripts created (migrate, migrate.bat)"
}

# Display next steps
show_next_steps() {
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "📝 Next Steps:"
    echo "1. Edit config.json with your Azure DevOps and GitHub settings"
    echo "2. Edit .env with your personal access tokens:"
    echo "   - AZURE_DEVOPS_PAT: Your Azure DevOps Personal Access Token"
    echo "   - GITHUB_TOKEN: Your GitHub Personal Access Token"
    echo ""
    echo "🚀 Usage Examples:"
    echo "   # Activate virtual environment"
    echo "   source venv/bin/activate  # Linux/Mac"
    echo "   venv\\Scripts\\activate.bat    # Windows"
    echo ""
    echo "   # Run single repository migration"
    echo "   python migrate.py --project 'MyProject' --repo 'my-repo'"
    echo ""
    echo "   # Run batch migration"
    echo "   python batch_migrate.py --plan sample_migration_plan.json"
    echo ""
    echo "   # Analyze organization"
    echo "   python analyze.py --create-plan"
    echo ""
    echo "📚 Documentation:"
    echo "   - README.md: General overview and usage"
    echo "   - HOW_TO_GUIDE.md: Step-by-step guide"
    echo "   - docs/: Detailed documentation"
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
    install_dependencies
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