#!/bin/bash
# Setup script for SceneBoard development

set -e

echo "🎸 Setting up SceneBoard..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and set your SECRET_KEY and database credentials"
fi

# Run migrations (will fail if DB not set up, but that's okay)
echo "Running migrations (may fail if database not configured)..."
python manage.py migrate || echo "⚠️  Migrations failed - database may not be configured yet"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration"
echo "2. Run: python manage.py migrate"
echo "3. Run: python manage.py createsuperuser"
echo "4. Run: python manage.py runserver"
echo ""
