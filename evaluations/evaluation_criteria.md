# Agent Evaluation Framework - Comprehensive Criteria

## Overview

This document defines the evaluation criteria and benchmarks for our AI agent system. Use this as a reference when running tests and interpreting results.

## Evaluation Categories

### 1. Tool Selection Accuracy (Weight: 20%)

**Criteria:**
- **Correct Tools Selected**: Does the agent choose the right tools for the query type?
- **Tool Combination Logic**: For complex queries, are multiple tools used effectively?
- **No Unnecessary Tools**: Are tools selected efficiently without redundancy?

**Benchmarks:**
- ✅ **Excellent (90-100)**: Perfect tool selection with logical combinations
- 🟡 **Good (70-89)**: Mostly correct with minor inefficiencies  
- 🔴 **Poor (0-69)**: Wrong tools or significant inefficiencies

**Test Scenarios:**
- Simple greetings → No tools needed
- Team discussions → Vector search
- Current events → Perplexity search
- Project docs → Atlassian search
- Complex queries → Multiple tools with synergy

### 2. Response Quality (Weight: 25%)

**Criteria:**
- **Answers Query**: Does the response directly address what the user asked?
- **Accuracy**: Is the information provided correct and reliable?
- **Completeness**: Is the response comprehensive enough for the context?
- **Clarity**: Is the response well-structured and easy to understand?
- **Actionability**: Does the response provide actionable next steps?

**Benchmarks:**
- ✅ **Excellent (90-100)**: Complete, accurate, clear, actionable
- 🟡 **Good (70-89)**: Mostly complete with minor gaps
- 🔴 **Poor (0-69)**: Incomplete, unclear, or inaccurate

**Quality Indicators:**
- No "technical difficulties" messages
- Specific information rather than generic responses
- Proper formatting with Slack markdown
- Logical flow and structure
- Relevant examples or details

### 3. Personality Application (Weight: 20%)

**Criteria:**
- **Contextual Adaptation**: Does personality adapt to user role and context?
- **Tone Appropriateness**: Is the tone suitable for the situation?
- **Design References**: Are design principles mentioned for design users?
- **Technical Depth**: Is technical detail appropriate for technical users?
- **Confidence Expression**: Is confidence level expressed appropriately?

**Benchmarks:**
- ✅ **Excellent (90-100)**: Perfect personality adaptation and expression
- 🟡 **Good (70-89)**: Good adaptation with minor mismatches
- 🔴 **Poor (0-69)**: Generic or inappropriate personality

**Personality Expectations:**

**For Design Users:**
- Reference design principles, UX patterns
- Use design vocabulary naturally
- Mention art history when contextually relevant
- Focus on user experience and visual aspects

**For Technical Users:**
- Use precise technical terminology
- Dive into implementation details
- Reference architecture and system concepts
- Provide technical depth and specificity

**For Management:**
- Focus on business impact and outcomes
- Provide strategic perspective
- Minimize humor, maintain professionalism
- Include timeline and resource considerations

**Context Adaptations:**
- **DMs**: More casual, can use first names, mention Construct when confident
- **Public Channels**: Professional, team-focused, inclusive language
- **High Confidence**: Assertive, definitive language
- **Low Confidence**: Exploratory, suggest verification steps

### 4. Source Integration (Weight: 15%)

**Criteria:**
- **Source Organization**: Are sources categorized and well-organized?
- **Source Relevance**: Are provided sources actually helpful?
- **Elegant Presentation**: Are sources presented beautifully, not as afterthoughts?

**Benchmarks:**
- ✅ **Excellent (90-100)**: Beautifully organized sources with clear categories
- 🟡 **Good (70-89)**: Well-organized with minor presentation issues
- 🔴 **Poor (0-69)**: Poor organization or irrelevant sources

**Expected Source Formatting:**
```
📚 *Documentation*
• <url|Confluence Page Title>
• <url|API Documentation>

🎫 *Project Tickets*  
• <url|JIRA-123: Feature Request>
• <url|JIRA-456: Bug Report>

🌐 *External Resources*
• <url|Industry Best Practices>
• <url|Technology Overview>

💬 *Team Discussions*
• <url|Slack Thread: Design Decision>
```

### 5. Performance (Weight: 10%)

**Criteria:**
- **Response Time**: Is response time within acceptable limits?
- **Timeout Handling**: Are timeouts handled gracefully?
- **Error Recovery**: Does the system recover well from errors?

**Benchmarks:**
- ✅ **Excellent (90-100)**: Fast responses with graceful error handling
- 🟡 **Good (70-89)**: Acceptable speed with minor timeout issues
- 🔴 **Poor (0-69)**: Slow responses or frequent timeouts

**Performance Targets:**
- **Simple queries**: < 10 seconds
- **Moderate queries**: < 25 seconds  
- **Complex queries**: < 45 seconds
- **Research queries**: < 60 seconds

### 6. Follow-up Quality (Weight: 10%)

**Criteria:**
- **Suggestion Relevance**: Are follow-up suggestions helpful and on-topic?
- **Contextual Suggestions**: Are suggestions adapted to user expertise?
- **Encourages Exploration**: Do suggestions promote helpful further interaction?

**Benchmarks:**
- ✅ **Excellent (90-100)**: Highly relevant, contextual suggestions
- 🟡 **Good (70-89)**: Good suggestions with minor relevance issues
- 🔴 **Poor (0-69)**: Generic or irrelevant suggestions

## Test Scenarios

### Simple Queries
- **Basic greetings and introductions**
- **Capability inquiries** 
- **Simple factual questions**
- Expected: Fast response, friendly tone, no tools needed

### Moderate Queries  
- **Team discussion searches**
- **Current technology trends**
- **Project documentation requests**
- Expected: Single tool usage, specific information, organized presentation

### Complex Queries
- **Multi-source investigations** 
- **Strategic analysis requests**
- **Design system guidance**
- Expected: Multiple tools, comprehensive synthesis, expert-level insights

### Error Handling
- **Ambiguous queries**
- **Invalid requests**
- **System limitations**
- Expected: Graceful handling, helpful guidance, clear explanations

### Performance Tests
- **Timeout stress tests**
- **Concurrent query handling**
- **Resource-intensive operations**
- Expected: Graceful degradation, timeout handling, fallback responses

## Scoring System

### Overall Score Calculation
```
Overall Score = (Tool Selection × 0.20) + 
                (Response Quality × 0.25) + 
                (Personality × 0.20) + 
                (Source Integration × 0.15) + 
                (Performance × 0.10) + 
                (Follow-up Quality × 0.10)
```

### Success Criteria
- **Score ≥ 85**: Excellent performance, system ready for production
- **Score 70-84**: Good performance, minor optimizations needed
- **Score 50-69**: Acceptable performance, significant improvements needed  
- **Score < 50**: Poor performance, major fixes required

### Critical Failure Conditions
- Response time > maximum threshold
- "Technical difficulties" error messages
- No response received
- Completely irrelevant responses
- System crashes or exceptions

## Usage Instructions

### Running Tests

**Quick Test (2 scenarios):**
```bash
python test_runner.py quick
```

**Full Test Suite (4 scenarios):**
```bash  
python test_runner.py full
```

### Interpreting Results

1. **Review Overall Metrics**: Look at success rate, average score, and response times
2. **Analyze Individual Tests**: Identify patterns in failures or low scores
3. **Check Recommendations**: Follow system-generated improvement suggestions
4. **Compare Baselines**: Track improvements over time

### Continuous Improvement

**After Code Changes:**
- Run quick test to verify no regressions
- Run full test suite before major deployments
- Track metrics over time to identify trends
- Use results to guide optimization priorities

**Performance Tracking:**
- Save test results with timestamps
- Compare against previous runs
- Set up automated testing for CI/CD
- Monitor production metrics alongside test results

## Best Practices

### Test Environment
- Use consistent test data and scenarios
- Run tests in isolated environment
- Ensure all dependencies are available
- Document any environmental factors

### Result Analysis
- Look for patterns across multiple runs
- Consider context when interpreting scores
- Focus on user experience implications
- Prioritize fixes based on impact and frequency

### Iteration Cycle
1. **Baseline**: Establish current performance levels
2. **Optimize**: Make targeted improvements
3. **Test**: Verify improvements with evaluation framework  
4. **Deploy**: Release with confidence
5. **Monitor**: Track real-world performance
6. **Repeat**: Continuous improvement cycle
