#!/bin/bash

# Pre-Deployment Testing Protocol
# MANDATORY: Run this script before every deployment

echo "🧪 Running Pre-Deployment Testing Protocol..."
echo "==============================================="

# Test 1: Health Check
echo "1. Testing health endpoint..."
HEALTH=$(curl -s http://localhost:5000/health 2>/dev/null)
if [[ $HEALTH == *"healthy"* ]]; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed: $HEALTH"
    exit 1
fi

# Test 2: System Status
echo "2. Testing system status..."
STATUS=$(curl -s http://localhost:5000/admin/system-status 2>/dev/null)
if [[ $STATUS == *"healthy"* ]]; then
    echo "   ✅ System status check passed"
else
    echo "   ❌ System status check failed: $STATUS"
    exit 1
fi

# Test 3: Agent Response
echo "3. Testing agent response..."
RESPONSE=$(curl -s "http://localhost:5000/admin/orchestrator-test?query=Hello" 2>/dev/null)
if [[ $RESPONSE == *"orchestrator_working"* ]] && [[ $RESPONSE == *"success"* ]]; then
    echo "   ✅ Agent response test passed"
else
    echo "   ❌ Agent response test failed: $RESPONSE"
    exit 1
fi

echo ""
echo "🎉 All tests passed! Server is ready for deployment."
echo "==============================================="