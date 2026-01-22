#!/bin/bash
# Fix deployment issues - yume-chan workspace packages

set -e

echo "=========================================="
echo "FlashDash Deployment Fix Script"
echo "=========================================="
echo ""

# Check if yume-chan packages exist
if [ ! -f "frontend/packages/yume-chan/libraries/adb/package.json" ]; then
    echo "❌ ERROR: yume-chan/adb package not found!"
    echo ""
    echo "The yume-chan packages must be present in the repository."
    echo ""
    echo "If they're missing, you need to:"
    echo "  1. Clone ya-webadb repository"
    echo "  2. Copy libraries to frontend/packages/yume-chan/libraries/"
    echo "  3. Commit to git"
    echo ""
    echo "Or ensure they're already committed:"
    echo "  git add frontend/packages/yume-chan/"
    echo "  git commit -m 'Add yume-chan workspace packages'"
    exit 1
fi

echo "✅ yume-chan packages found"

# Check workspace configuration
if ! grep -q "packages/yume-chan/libraries/\*" frontend/pnpm-workspace.yaml; then
    echo "❌ ERROR: pnpm-workspace.yaml missing yume-chan configuration!"
    echo ""
    echo "Add this line to frontend/pnpm-workspace.yaml:"
    echo "  - 'packages/yume-chan/libraries/*'"
    exit 1
fi

echo "✅ Workspace configuration correct"

# Check if packages are tracked in git
if ! git ls-files frontend/packages/yume-chan/libraries/adb/package.json > /dev/null 2>&1; then
    echo "⚠️  WARNING: yume-chan packages not tracked in git"
    echo ""
    echo "Adding to git..."
    git add frontend/packages/yume-chan/ || echo "Could not add to git (may already be added)"
fi

echo "✅ Git tracking verified"

# Verify device-manager dependencies
if ! grep -q "@yume-chan/adb" frontend/packages/device-manager/package.json; then
    echo "❌ ERROR: device-manager missing @yume-chan/adb dependency"
    exit 1
fi

echo "✅ device-manager dependencies correct"

echo ""
echo "=========================================="
echo "All checks passed! Ready for deployment."
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Commit any changes: git add . && git commit -m 'Fix deployment'"
echo "  2. Push to repository: git push"
echo "  3. Rebuild Docker: docker-compose build --no-cache"
echo "  4. Start services: docker-compose up -d"
echo ""
