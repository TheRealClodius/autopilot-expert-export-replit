# Agent Evaluation System

A comprehensive evaluation framework for testing and benchmarking the AI agent system performance, quality, and reliability.

## 🎯 Overview

This evaluation system provides sophisticated testing capabilities for:
- **Orchestrator Agent**: 5-step reasoning, tool selection, synthesis quality
- **Client Agent**: Personality application, contextual adaptation, source integration  
- **System Performance**: Response times, timeout handling, error recovery
- **User Experience**: Response quality, follow-up suggestions, overall satisfaction

## 📁 Files

### Core Files
- `test_runner.py` - Main evaluation framework with comprehensive test scenarios
- `evaluation_criteria.md` - Detailed scoring criteria and benchmarks
- `simple_test.py` - Basic framework verification (no environment setup required)

### Generated Files  
- `test_results_*.json` - Test execution results with timestamps
- `simple_test_result_*.json` - Framework verification results

## 🚀 Quick Start

### 1. Verify Framework Works
```bash
cd evaluations
uv run python simple_test.py
```
Expected: Framework verification with 100/100 score

### 2. Run Quick Agent Test (2 scenarios)
```bash
cd evaluations
uv run python test_runner.py quick
```
Expected: Basic greeting + team discussion search tests

### 3. Run Full Test Suite (4 scenarios)  
```bash
cd evaluations
uv run python test_runner.py full
```
Expected: Comprehensive evaluation across all complexity levels

### 4. Enable LLM-Enhanced Evaluation
```bash
cd evaluations

# Set your API key (required for LLM evaluation)
export DEEPSEEK_API_KEY="your_api_key_here"

# Run with LLM enhancement
uv run python test_runner.py quick --llm
uv run python test_runner.py full --llm
```
Expected: Hybrid evaluation with both Python-based and LLM-based scoring

### Alternative: Run from project root
```bash
# From project root directory
uv run python evaluations/simple_test.py
uv run python evaluations/test_runner.py quick [--llm]
uv run python evaluations/test_runner.py full [--llm]
```

## 🧠 Evaluation Methods

The framework supports two evaluation approaches that can be combined:

### Python-Based Evaluation (Default)
- ✅ **Fast & Deterministic**: Same input always gives same score
- ✅ **No API costs**: Uses programmatic criteria  
- ✅ **Transparent**: Clear, inspectable scoring logic
- 📊 **Criteria**: Response length, error detection, keyword matching, timing

### LLM-Enhanced Evaluation (Optional)
- 🤖 **Sophisticated**: Nuanced quality assessment using DeepSeek AI
- 🎯 **Context-aware**: Considers user role and query complexity
- 📈 **Detailed**: Helpfulness, clarity, professionalism, accuracy
- 💰 **API costs**: Requires DEEPSEEK_API_KEY and uses API calls

### Hybrid Mode (Recommended)
When LLM evaluation is enabled, scores are combined:
- **Response Quality**: 60% Python + 40% LLM scores
- **Other Categories**: Python-based with LLM context awareness
- **Fallback**: Gracefully degrades to Python-only if LLM fails

## 📊 Test Scenarios

### Simple Queries
- **Basic Greeting**: Tests personality, name usage, friendly tone
- **Capability Inquiry**: Tests technical depth, professional tone

### Moderate Queries  
- **Team Discussion Search**: Tests vector search tool selection and synthesis
- **Complex Investigation**: Tests multi-tool coordination and comprehensive analysis

### Stress Tests
- **Timeout Resilience**: Tests graceful degradation under complex loads
- **Error Handling**: Tests response to ambiguous or invalid queries

## 🎯 Evaluation Categories

| Category | Weight | Focus Area |
|----------|--------|------------|
| **Tool Selection** | 20% | Correct tool choice, logical combinations |
| **Response Quality** | 25% | Accuracy, completeness, clarity, actionability |
| **Personality Application** | 20% | Context adaptation, tone, design/technical depth |
| **Source Integration** | 15% | Organization, relevance, elegant presentation |
| **Performance** | 10% | Response times, timeout handling, error recovery |
| **Follow-up Quality** | 10% | Suggestion relevance, contextual adaptation |

## 📈 Scoring System

### Score Ranges
- **🟢 Excellent (85-100)**: Production ready, excellent user experience
- **🟡 Good (70-84)**: Minor optimizations needed, generally reliable  
- **🔴 Poor (50-69)**: Significant improvements required
- **💥 Critical (<50)**: Major fixes needed before deployment

### Success Criteria
- Overall score ≥ 70
- No "technical difficulties" errors
- Response times within thresholds
- Proper personality application
- Organized source presentation

## 🛠 Usage Patterns

### After Code Changes
```bash
cd evaluations

# Quick regression test (Python-based)
uv run python test_runner.py quick

# Enhanced quality check (requires API key)
uv run python test_runner.py quick --llm

# If quick test passes, run full suite
uv run python test_runner.py full --llm
```

### Before Deployment
```bash
cd evaluations

# Full evaluation with LLM enhancement (recommended)
export DEEPSEEK_API_KEY="your_api_key"
uv run python test_runner.py full --llm

# Review results and recommendations
cat test_results_*_hybrid_*.json | grep -A 5 "recommendations"
```

### Performance Monitoring
```bash
cd evaluations

# Regular baseline testing
uv run python test_runner.py quick

# Detailed quality assessment (weekly/monthly)
uv run python test_runner.py full --llm

# Track improvements over time
ls test_results_*.json | sort
```

### Evaluation Method Selection
```bash
# Fast feedback loop (no API costs)
uv run python test_runner.py quick

# Quality assurance (uses API, more detailed)
uv run python test_runner.py quick --llm

# Production readiness check (comprehensive)
uv run python test_runner.py full --llm
```

## 📋 Test Results Analysis

### Interpreting Scores

**Tool Selection (20% weight):**
- 90-100: Perfect tool choices with logical combinations
- 70-89: Mostly correct with minor inefficiencies  
- 0-69: Wrong tools or significant inefficiencies

**Response Quality (25% weight):**
- 90-100: Complete, accurate, clear, actionable responses
- 70-89: Good responses with minor gaps
- 0-69: Incomplete, unclear, or inaccurate responses

**Personality Application (20% weight):**
- 90-100: Perfect adaptation to user role and context
- 70-89: Good adaptation with minor mismatches
- 0-69: Generic or inappropriate personality

### Common Issues and Solutions

**Low Tool Selection Scores:**
- Review prompt engineering for tool selection logic
- Check keyword detection in orchestrator planning
- Verify tool availability and error handling

**Poor Response Quality:**
- Examine synthesis prompts and temperature settings
- Review timeout handling and fallback responses
- Check for "technical difficulties" error patterns

**Weak Personality Application:**
- Verify client agent contextual adaptation logic  
- Review temperature settings (currently 1.0 for creativity)
- Check user role detection and personality mapping

**Slow Performance:**
- Review timeout settings (recently optimized: 15s, 8s, 12s)
- Check for LLM request bottlenecks
- Verify tool execution efficiency

## 🔧 Customization

### Adding New Test Scenarios
Edit `evaluations/test_runner.py` and add to `_create_test_scenarios()`:

```python
{
    "id": "custom_test",
    "name": "Custom Test Name", 
    "query": "Your test query here",
    "user_context": {
        "first_name": "TestUser",
        "title": "Role",
        "department": "Department"
    },
    "channel_context": {
        "is_dm": True/False,
        "channel_name": "channel"
    },
    "expectations": {
        "max_response_time": 30.0,
        "min_response_length": 100,
        "custom_criteria": True
    }
}
```

### Adjusting Evaluation Criteria
Modify `_evaluate_response()` in `evaluations/test_runner.py` to add custom scoring logic.

### Custom Test Suites
Create new functions in `AgentTestRunner` class:
```python
async def run_custom_test(self) -> Dict[str, Any]:
    custom_scenarios = ["test_id_1", "test_id_2"] 
    return await self.run_tests(custom_scenarios)
```

## 📝 Best Practices

### Regular Testing
- Run quick tests after any agent code changes
- Run full tests before production deployments  
- Establish baseline metrics for comparison
- Track performance trends over time

### Result Analysis
- Focus on patterns across multiple test runs
- Prioritize fixes based on score impact and frequency
- Compare against historical results to track improvements
- Use recommendations to guide optimization efforts

### Continuous Improvement
1. **Baseline**: Establish current performance with full test
2. **Optimize**: Make targeted improvements based on results
3. **Verify**: Run tests to confirm improvements
4. **Deploy**: Release with confidence
5. **Monitor**: Track real-world performance
6. **Iterate**: Repeat cycle for continuous enhancement

## 🎯 Integration with Development Workflow

### Git Hooks (Recommended)
```bash
# Pre-commit hook
#!/bin/bash
echo "Running agent evaluation..."
cd evaluations && uv run python test_runner.py quick
if [ $? -ne 0 ]; then
    echo "❌ Agent tests failed - commit blocked"
    exit 1
fi
echo "✅ Agent tests passed"
```

### CI/CD Integration
- Run quick tests on every commit
- Run full tests on pull requests
- Block deployments if score drops below threshold
- Generate performance trend reports

### Production Monitoring
- Correlate test scores with real user feedback
- Use evaluation criteria to assess production incidents
- Regular production evaluations using similar scenarios
- Automated alerting for performance degradation

## 🏆 Success Metrics

Track these key metrics over time:
- **Overall Score Trend**: Should increase with improvements
- **Success Rate**: Percentage of tests passing
- **Response Time Trend**: Should decrease with optimizations  
- **Error Rate**: Should approach zero
- **User Satisfaction**: Correlate with test scores

## 📞 Troubleshooting

### Framework Issues
- Run `evaluations/simple_test.py` to verify framework functionality
- Check Python environment and dependencies
- Review error logs for specific failure patterns

### Agent Issues  
- Check environment variables (SLACK_BOT_TOKEN, DEEPSEEK_API_KEY)
- Verify service dependencies (memory, embedding, etc.)
- Review agent logs during test execution

### Performance Issues
- Monitor system resources during test execution
- Check for network latency or API rate limits
- Review timeout settings and fallback mechanisms

---

**Last Updated**: 2025-07-01  
**Framework Version**: 1.0  
**Compatible Agent Version**: Enhanced orchestrator + client agent system
