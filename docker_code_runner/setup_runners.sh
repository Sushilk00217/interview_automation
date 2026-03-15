#!/bin/bash

# Exit on error
set -e

echo "🔨 Building Docker Code Runners..."

# Navigate to the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "🐍 Building Python runner..."
docker build -t code-runner-python -f python.Dockerfile .

echo "📦 Building Node.js runner..."
docker build -t code-runner-node -f node.Dockerfile .

echo "☕ Building Java runner..."
docker build -t code-runner-java -f java.Dockerfile .

echo "🔨 Building C++ runner..."
docker build -t code-runner-cpp -f cpp.Dockerfile .

echo "✅ All runners built successfully!"
docker images | grep code-runner
