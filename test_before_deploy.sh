#!/bin/bash

# Pre-Deployment Test Protocol for Multi-Agent Slack System
# Validates all critical components before production deployment

echo "🚀 PRE-DEPLOYMENT TEST PROTOCOL"
echo "================================"

# Test 1: Health Check
echo "1️⃣ Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:5000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed: $HEALTH_RESPONSE"
    exit 1
fi

# Test 2: System Status
echo -e "\n2️⃣ Testing system status..."
STATUS_RESPONSE=$(curl -s http://localhost:5000/admin/system-status)
if echo "$STATUS_RESPONSE" | grep -q "services_initialized.*true"; then
    echo "✅ System status healthy"
else
    echo "❌ System status failed: $STATUS_RESPONSE"
    exit 1
fi

# Test 3: API Connectivity
echo -e "\n3️⃣ Testing API connectivity..."
API_RESPONSE=$(curl -s http://localhost:5000/admin/api-test)
PASSED_APIS=$(echo "$API_RESPONSE" | grep -o '"passed":[0-9]*' | cut -d':' -f2)
if [ "$PASSED_APIS" -ge 3 ]; then
    echo "✅ API connectivity passed ($PASSED_APIS/4 APIs working)"
else
    echo "❌ API connectivity failed: only $PASSED_APIS APIs working"
    exit 1
fi

# Test 4: Prompt Loading
echo -e "\n4️⃣ Testing prompt loading..."
PROMPT_RESPONSE=$(curl -s http://localhost:5000/admin/prompts)
if echo "$PROMPT_RESPONSE" | grep -q "prompts_loaded.*6"; then
    echo "✅ All prompts loaded correctly"
else
    echo "❌ Prompt loading failed: $PROMPT_RESPONSE"
    exit 1
fi

# Test 5: Orchestrator Intelligence (No Tools)
echo -e "\n5️⃣ Testing orchestrator intelligence (conversational)..."
CONV_RESPONSE=$(curl -s "http://localhost:5000/admin/orchestrator-test?query=Hello%20there" --max-time 10)
if echo "$CONV_RESPONSE" | grep -q '"tools_needed":\[\]'; then
    echo "✅ Orchestrator correctly identifies conversational requests (no tools)"
else
    echo "❌ Orchestrator intelligence failed for conversational requests"
    exit 1
fi

# Test 6: Orchestrator Intelligence (With Tools)
echo -e "\n6️⃣ Testing orchestrator intelligence (technical)..."
TECH_RESPONSE=$(curl -s "http://localhost:5000/admin/orchestrator-test?query=What%20are%20Autopilot%20features" --max-time 10)
if echo "$TECH_RESPONSE" | grep -q '"tools_needed":\["vector_search"\]'; then
    echo "✅ Orchestrator correctly identifies technical requests (with tools)"
else
    echo "❌ Orchestrator intelligence failed for technical requests"
    exit 1
fi

# Test 7: LangSmith Tracing
echo -e "\n7️⃣ Testing LangSmith tracing..."
TRACE_RESPONSE=$(curl -s http://localhost:5000/admin/langsmith-test)
if echo "$TRACE_RESPONSE" | grep -q "conversation_complete"; then
    echo "✅ LangSmith tracing operational with conversation completion"
else
    echo "❌ LangSmith tracing failed: $TRACE_RESPONSE"
    exit 1
fi

echo -e "\n🎉 ALL PRE-DEPLOYMENT TESTS PASSED!"
echo "================================"
echo "✅ Health endpoints operational"
echo "✅ System services initialized"
echo "✅ External APIs connected (3/4 minimum)"
echo "✅ All prompts loaded correctly"
echo "✅ Intelligent orchestrator decision making"
echo "✅ LangSmith observability working"
echo -e "\n🚀 SYSTEM READY FOR DEPLOYMENT"