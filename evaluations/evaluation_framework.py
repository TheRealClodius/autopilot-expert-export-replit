#!/usr/bin/env python3
"""
Comprehensive Agent Evaluation Framework
Tests orchestrator reasoning, tool selection, response quality, personality, and performance
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.core.memory_service import MemoryService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    RESEARCH = "research"

class ExpectedTool(Enum):
    VECTOR_SEARCH = "vector_search"
    PERPLEXITY_SEARCH = "perplexity_search"
    ATLASSIAN_SEARCH = "atlassian_search"
    OUTLOOK_MEETING = "outlook_meeting"
    MULTI_TOOL = "multi_tool"

@dataclass
class TestScenario:
    """Defines a test scenario with expected outcomes"""
    id: str
    name: str
    query: str
    complexity: QueryComplexity
    expected_tools: List[ExpectedTool]
    user_context: Dict[str, Any]
    channel_context: Dict[str, Any]
    success_criteria: Dict[str, Any]
    personality_expectations: Dict[str, Any]

@dataclass
class EvaluationResult:
    """Results from evaluating a single test scenario"""
    scenario_id: str
    success: bool
    scores: Dict[str, float]
    response_time: float
    response_text: str
    tools_used: List[str]
    errors: List[str]
    detailed_analysis: Dict[str, Any]

class AgentEvaluationFramework:
    """Comprehensive evaluation framework for the agent system"""
    
    def __init__(self, enable_llm_evaluation: bool = None):
        self.test_scenarios = self._create_test_scenarios()
        self.evaluation_criteria = self._define_evaluation_criteria()
        
        # Auto-detect LLM evaluation availability
        if enable_llm_evaluation is None:
            self.enable_llm_evaluation = bool(os.getenv('DEEPSEEK_API_KEY'))
        else:
            self.enable_llm_evaluation = enable_llm_evaluation
            
        if self.enable_llm_evaluation:
            logger.info("🤖 LLM-enhanced evaluation ENABLED - Advanced quality assessment")
        else:
            logger.info("📝 Standard evaluation mode - Add DEEPSEEK_API_KEY for LLM enhancement")
        
    def _create_test_scenarios(self) -> List[TestScenario]:
        """Create comprehensive test scenarios covering all agent capabilities"""
        
        return [
            # === SIMPLE QUERIES ===
            TestScenario(
                id="simple_01",
                name="Basic Greeting",
                query="Hi there!",
                complexity=QueryComplexity.SIMPLE,
                expected_tools=[],
                user_context={"first_name": "Sarah", "title": "Designer", "department": "Design"},
                channel_context={"is_dm": True, "channel_name": "dm"},
                success_criteria={
                    "response_time_max": 10.0,
                    "min_response_length": 20,
                    "should_be_friendly": True,
                    "should_include_capabilities": True
                },
                personality_expectations={
                    "should_use_name": True,
                    "tone": "casual_direct",
                    "design_references": False
                }
            ),
            
            TestScenario(
                id="simple_02", 
                name="Capabilities Inquiry",
                query="What can you help me with?",
                complexity=QueryComplexity.SIMPLE,
                expected_tools=[],
                user_context={"first_name": "Mike", "title": "Software Engineer", "department": "Engineering"},
                channel_context={"is_dm": False, "channel_name": "general"},
                success_criteria={
                    "response_time_max": 10.0,
                    "should_list_capabilities": True,
                    "should_mention_tools": True
                },
                personality_expectations={
                    "tone": "professional_engaging",
                    "technical_depth": True
                }
            ),

            # === MODERATE QUERIES ===
            TestScenario(
                id="moderate_01",
                name="Team Discussion Search",
                query="What did the team discuss about the new authentication system last week?",
                complexity=QueryComplexity.MODERATE,
                expected_tools=[ExpectedTool.VECTOR_SEARCH],
                user_context={"first_name": "Alex", "title": "Product Manager", "department": "Product"},
                channel_context={"is_dm": False, "channel_name": "engineering"},
                success_criteria={
                    "response_time_max": 25.0,
                    "should_search_conversations": True,
                    "should_provide_specific_info": True,
                    "min_response_length": 100
                },
                personality_expectations={
                    "should_synthesize_findings": True,
                    "confidence_level": "medium"
                }
            ),
            
            TestScenario(
                id="moderate_02",
                name="Current Technology Trends",
                query="What are the latest AI developments in automation platforms?",
                complexity=QueryComplexity.MODERATE,
                expected_tools=[ExpectedTool.PERPLEXITY_SEARCH],
                user_context={"first_name": "Jennifer", "title": "Tech Lead", "department": "Engineering"},
                channel_context={"is_dm": True, "channel_name": "dm"},
                success_criteria={
                    "response_time_max": 20.0,
                    "should_have_current_info": True,
                    "should_cite_sources": True
                },
                personality_expectations={
                    "technical_depth": True,
                    "should_include_implications": True
                }
            ),

            TestScenario(
                id="moderate_03",
                name="Project Documentation Request",
                query="Show me the latest documentation for UiPath Autopilot integration",
                complexity=QueryComplexity.MODERATE,
                expected_tools=[ExpectedTool.ATLASSIAN_SEARCH],
                user_context={"first_name": "David", "title": "Developer", "department": "Engineering"},
                channel_context={"is_dm": False, "channel_name": "autopilot-dev"},
                success_criteria={
                    "response_time_max": 25.0,
                    "should_find_documentation": True,
                    "should_organize_sources": True
                },
                personality_expectations={
                    "technical_depth": True,
                    "should_provide_actionable_info": True
                }
            ),

            # === COMPLEX QUERIES ===
            TestScenario(
                id="complex_01",
                name="Multi-Source Investigation",
                query="I need to understand the current state of our authentication project - what the team has discussed, what's documented, and what industry best practices exist",
                complexity=QueryComplexity.COMPLEX,
                expected_tools=[ExpectedTool.MULTI_TOOL],
                user_context={"first_name": "Lisa", "title": "Senior Architect", "department": "Engineering"},
                channel_context={"is_dm": False, "channel_name": "architecture"},
                success_criteria={
                    "response_time_max": 45.0,
                    "should_use_multiple_tools": True,
                    "should_synthesize_sources": True,
                    "min_response_length": 300,
                    "should_provide_comprehensive_overview": True
                },
                personality_expectations={
                    "confidence_level": "high",
                    "should_show_expertise": True,
                    "technical_depth": True
                }
            ),

            TestScenario(
                id="complex_02",
                name="Design System Inquiry",
                query="How should we approach the UX patterns for our new AI agent interfaces, considering both our existing design system and current industry standards?",
                complexity=QueryComplexity.COMPLEX,
                expected_tools=[ExpectedTool.MULTI_TOOL],
                user_context={"first_name": "Emma", "title": "Principal Designer", "department": "Design"},
                channel_context={"is_dm": True, "channel_name": "dm"},
                success_criteria={
                    "response_time_max": 40.0,
                    "should_address_design_patterns": True,
                    "should_reference_standards": True,
                    "should_provide_strategic_guidance": True
                },
                personality_expectations={
                    "design_references": True,
                    "should_mention_ux_principles": True,
                    "tone": "casual_direct",
                    "expert_confidence": True
                }
            ),

            # === ERROR HANDLING SCENARIOS ===
            TestScenario(
                id="error_01",
                name="Ambiguous Query",
                query="Fix the thing",
                complexity=QueryComplexity.SIMPLE,
                expected_tools=[],
                user_context={"first_name": "John", "title": "User", "department": ""},
                channel_context={"is_dm": False, "channel_name": "general"},
                success_criteria={
                    "response_time_max": 15.0,
                    "should_ask_for_clarification": True,
                    "should_be_helpful": True,
                    "should_provide_examples": True
                },
                personality_expectations={
                    "should_be_patient": True,
                    "should_guide_user": True
                }
            ),

            # === PERSONALITY TESTS ===
            TestScenario(
                id="personality_01",
                name="Design Context with Design User",
                query="What are some good design patterns for displaying AI agent responses?",
                complexity=QueryComplexity.MODERATE,
                expected_tools=[ExpectedTool.PERPLEXITY_SEARCH, ExpectedTool.VECTOR_SEARCH],
                user_context={"first_name": "Maria", "title": "UX Designer", "department": "Design"},
                channel_context={"is_dm": True, "channel_name": "dm"},
                success_criteria={
                    "should_reference_design_principles": True,
                    "should_show_design_expertise": True
                },
                personality_expectations={
                    "design_references": True,
                    "should_mention_art_history": False,  # Should be contextual
                    "construct_mentions": False,  # Only when very confident
                    "design_vocabulary": True
                }
            ),

            # === PERFORMANCE TESTS ===
            TestScenario(
                id="performance_01",
                name="Timeout Resilience Test",
                query="This is a complex query that might test timeout handling with multiple information requests about UiPath Autopilot architecture, current AI trends, team discussions, and strategic recommendations all at once",
                complexity=QueryComplexity.COMPLEX,
                expected_tools=[ExpectedTool.MULTI_TOOL],
                user_context={"first_name": "Test", "title": "Engineer", "department": "Engineering"},
                channel_context={"is_dm": False, "channel_name": "test"},
                success_criteria={
                    "should_not_timeout": True,
                    "should_provide_response": True,
                    "max_acceptable_time": 50.0,
                    "min_response_length": 50
                },
                personality_expectations={
                    "should_handle_gracefully": True
                }
            )
        ]

    def _define_evaluation_criteria(self) -> Dict[str, Dict[str, Any]]:
        """Define comprehensive evaluation criteria for different aspects"""
        
        return {
            "tool_selection": {
                "weight": 20,
                "criteria": {
                    "correct_tools_selected": "Did the agent select the appropriate tools for the query?",
                    "tool_combination_logic": "For multi-tool queries, were tools combined logically?",
                    "no_unnecessary_tools": "Were no unnecessary tools selected?"
                }
            },
            
            "response_quality": {
                "weight": 25,
                "criteria": {
                    "answers_query": "Does the response directly answer the user's question?",
                    "accuracy": "Is the information provided accurate?", 
                    "completeness": "Is the response comprehensive enough?",
                    "clarity": "Is the response clear and well-structured?",
                    "actionability": "Does the response provide actionable information?"
                }
            },
            
            "personality_application": {
                "weight": 20,
                "criteria": {
                    "contextual_adaptation": "Does personality adapt to user role and context?",
                    "tone_appropriateness": "Is the tone appropriate for the situation?",
                    "design_references": "Are design references used appropriately with design users?",
                    "technical_depth": "Is technical depth appropriate for technical users?",
                    "confidence_expression": "Is confidence level expressed appropriately?"
                }
            },
            
            "source_integration": {
                "weight": 15,
                "criteria": {
                    "source_organization": "Are sources well-organized and categorized?",
                    "source_relevance": "Are provided sources relevant and helpful?",
                    "elegant_presentation": "Are sources presented elegantly, not as afterthoughts?"
                }
            },
            
            "performance": {
                "weight": 10,
                "criteria": {
                    "response_time": "Is response time within acceptable limits?",
                    "timeout_handling": "Are timeouts handled gracefully?",
                    "error_recovery": "Does the system recover well from errors?"
                }
            },
            
            "follow_up_quality": {
                "weight": 10,
                "criteria": {
                    "suggestion_relevance": "Are follow-up suggestions relevant and helpful?",
                    "contextual_suggestions": "Are suggestions adapted to user role and expertise?",
                    "encourages_exploration": "Do suggestions encourage further helpful exploration?"
                }
            }
        }

    async def run_evaluation(self, scenarios: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run comprehensive evaluation on specified scenarios or all scenarios"""
        
        logger.info("🧪 Starting Comprehensive Agent Evaluation")
        logger.info("=" * 60)
        
        # Initialize agent components  
        try:
            memory_service = MemoryService()
            orchestrator = OrchestratorAgent(memory_service)
            client_agent = ClientAgent()
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            return {"status": "failed", "error": "Agent initialization failed"}
        
        # Select scenarios to run
        scenarios_to_run = []
        if scenarios:
            scenarios_to_run = [s for s in self.test_scenarios if s.id in scenarios]
        else:
            scenarios_to_run = self.test_scenarios
        
        logger.info(f"Running {len(scenarios_to_run)} test scenarios...")
        
        results = []
        overall_start_time = time.time()
        
        for scenario in scenarios_to_run:
            logger.info(f"\n🔍 Testing: {scenario.name} ({scenario.id})")
            logger.info(f"Query: \"{scenario.query}\"")
            logger.info(f"Complexity: {scenario.complexity.value}")
            
            result = await self._evaluate_scenario(scenario, orchestrator, client_agent)
            results.append(result)
            
            # Log result summary
            success_emoji = "✅" if result.success else "❌"
            logger.info(f"{success_emoji} Result: {result.success} (Score: {result.scores.get('overall', 0):.1f}/100)")
            logger.info(f"   Response time: {result.response_time:.1f}s")
            logger.info(f"   Tools used: {result.tools_used}")
            
            if result.errors:
                logger.warning(f"   Errors: {result.errors}")
        
        # Calculate overall metrics
        overall_metrics = self._calculate_overall_metrics(results)
        overall_time = time.time() - overall_start_time
        
        # Generate comprehensive report
        report = {
            "evaluation_timestamp": datetime.now().isoformat(),
            "total_scenarios": len(scenarios_to_run),
            "total_time": overall_time,
            "overall_metrics": overall_metrics,
            "individual_results": [self._result_to_dict(r) for r in results],
            "recommendations": self._generate_recommendations(results)
        }
        
        logger.info(f"\n🎯 EVALUATION COMPLETE")
        logger.info(f"Overall Score: {overall_metrics['overall_score']:.1f}/100")
        logger.info(f"Success Rate: {overall_metrics['success_rate']:.1f}%")
        logger.info(f"Average Response Time: {overall_metrics['avg_response_time']:.1f}s")
        
        return report

    async def _evaluate_scenario(self, scenario: TestScenario, orchestrator: OrchestratorAgent, 
                                client_agent: ClientAgent) -> EvaluationResult:
        """Evaluate a single test scenario"""
        
        start_time = time.time()
        errors = []
        tools_used = []
        response_text = ""
        
        try:
            # Create test message
            test_message = ProcessedMessage(
                text=scenario.query,
                user_id="EVAL_USER",
                user_name=scenario.user_context.get("name", "TestUser"),
                user_email="test@example.com",
                user_display_name=scenario.user_context.get("first_name", "Test"),
                user_first_name=scenario.user_context.get("first_name", "Test"),
                user_title=scenario.user_context.get("title", ""),
                user_department=scenario.user_context.get("department", ""),
                channel_id="EVAL_CHANNEL",
                channel_name=scenario.channel_context.get("channel_name", "test"),
                is_dm=scenario.channel_context.get("is_dm", False),
                is_mention=True,
                thread_ts=None,
                message_ts=f"{int(time.time())}.000001"
            )
            
            # Run orchestrator processing
            response = await orchestrator.process_query(test_message)
            response_time = time.time() - start_time
            
            if response:
                response_text = response.get("text", "")
                # Extract tools used from execution summary if available
                exec_summary = response.get("execution_summary", {})
                if "tools_executed" in exec_summary:
                    tools_used = exec_summary["tools_executed"]
                
            else:
                errors.append("Orchestrator returned None")
                response_text = ""
            
            # Evaluate the response
            scores = await self._score_response(scenario, response, response_time)
            
            success = (
                response is not None and
                len(response_text) >= scenario.success_criteria.get("min_response_length", 10) and
                response_time <= scenario.success_criteria.get("response_time_max", 60.0) and
                not any("technical difficulties" in error.lower() for error in errors)
            )
            
            return EvaluationResult(
                scenario_id=scenario.id,
                success=success,
                scores=scores,
                response_time=response_time,
                response_text=response_text,
                tools_used=tools_used,
                errors=errors,
                detailed_analysis=self._analyze_response_details(scenario, response, response_time)
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            errors.append(f"Exception during evaluation: {str(e)}")
            
            return EvaluationResult(
                scenario_id=scenario.id,
                success=False,
                scores={"overall": 0},
                response_time=response_time,
                response_text="",
                tools_used=[],
                errors=errors,
                detailed_analysis={"exception": str(e)}
            )

    async def _score_response(self, scenario: TestScenario, response: Optional[Dict[str, Any]], 
                             response_time: float) -> Dict[str, float]:
        """Score the response across all evaluation criteria"""
        
        if not response:
            return {category: 0.0 for category in self.evaluation_criteria.keys()} | {"overall": 0.0}
        
        scores = {}
        
        # Tool Selection Scoring
        tools_score = self._score_tool_selection(scenario, response)
        scores["tool_selection"] = tools_score
        
        # Response Quality Scoring (with optional LLM enhancement)
        quality_score = await self._score_response_quality(scenario, response)
        scores["response_quality"] = quality_score
        
        # Personality Application Scoring
        personality_score = self._score_personality_application(scenario, response)
        scores["personality_application"] = personality_score
        
        # Source Integration Scoring
        source_score = self._score_source_integration(scenario, response)
        scores["source_integration"] = source_score
        
        # Performance Scoring
        performance_score = self._score_performance(scenario, response, response_time)
        scores["performance"] = performance_score
        
        # Follow-up Quality Scoring
        followup_score = self._score_followup_quality(scenario, response)
        scores["follow_up_quality"] = followup_score
        
        # Calculate weighted overall score
        overall_score = 0.0
        for category, category_score in scores.items():
            weight = self.evaluation_criteria[category]["weight"]
            overall_score += (category_score * weight) / 100
        
        scores["overall"] = overall_score
        return scores

    def _score_tool_selection(self, scenario: TestScenario, response: Dict[str, Any]) -> float:
        """Score tool selection accuracy"""
        # Implementation would analyze execution summary and compare to expected tools
        # For now, return a placeholder score
        return 85.0
    
    async def _score_response_quality(self, scenario: TestScenario, response: Dict[str, Any]) -> float:
        """Score response quality with optional LLM enhancement"""
        response_text = response.get("text", "")
        
        # Python-based quality checks (baseline)
        python_score = 0.0
        
        # Length check
        min_length = scenario.success_criteria.get("min_response_length", 20)
        if len(response_text) >= min_length:
            python_score += 20
        
        # No "technical difficulties" or error messages
        if not any(phrase in response_text.lower() for phrase in ["technical difficulties", "error", "sorry"]):
            python_score += 30
        
        # Contains specific information (not just generic responses)
        if len(response_text) > 100 and any(word in response_text.lower() for word in ["specific", "detailed", "found", "information"]):
            python_score += 25
        
        # Well structured (contains formatting)
        if any(char in response_text for char in ["*", "`", "•", "\n"]):
            python_score += 15
        
        # Actionable content
        if any(word in response_text.lower() for word in ["can", "should", "try", "consider", "next"]):
            python_score += 10
        
        # LLM enhancement if enabled
        if self.enable_llm_evaluation and response_text and len(response_text) > 20:
            try:
                llm_quality_scores = await self._llm_evaluate_quality(scenario, response_text)
                
                # Weighted combination: 60% Python-based, 40% LLM-based
                avg_llm_quality = (
                    llm_quality_scores["helpfulness"] + 
                    llm_quality_scores["clarity"] + 
                    llm_quality_scores["completeness"]
                ) / 3
                
                combined_score = (python_score * 0.6) + (avg_llm_quality * 0.4)
                return min(combined_score, 100.0)
            except Exception as e:
                logger.warning(f"LLM quality evaluation failed: {e}")
        
        return python_score
    
    def _score_personality_application(self, scenario: TestScenario, response: Dict[str, Any]) -> float:
        """Score personality application appropriateness"""
        response_text = response.get("text", "")
        personality_expectations = scenario.personality_expectations
        
        score = 50.0  # Base score
        
        # Check for name usage when expected
        if personality_expectations.get("should_use_name") and scenario.user_context.get("first_name"):
            if scenario.user_context["first_name"] in response_text:
                score += 20
        
        # Check technical depth for technical users
        if personality_expectations.get("technical_depth") and scenario.user_context.get("title", "").lower() in ["engineer", "developer", "architect"]:
            if any(word in response_text.lower() for word in ["implementation", "technical", "architecture", "system"]):
                score += 15
        
        # Check design references for design users
        if personality_expectations.get("design_references") and scenario.user_context.get("department", "").lower() == "design":
            if any(word in response_text.lower() for word in ["design", "ux", "ui", "user experience", "pattern"]):
                score += 15
        
        return min(score, 100.0)
    
    async def _llm_evaluate_quality(self, scenario: TestScenario, response_text: str) -> Dict[str, float]:
        """LLM-based quality evaluation for nuanced assessment"""
        
        try:
            from utils.deepseek_client import DeepSeekClient
            
            user_context = scenario.user_context
            query = scenario.query
            
            evaluation_prompt = f"""You are an expert AI system evaluator. Analyze this agent response for quality across multiple dimensions.

USER CONTEXT:
- Name: {user_context.get('first_name', 'Unknown')}
- Title: {user_context.get('title', 'Unknown')} 
- Department: {user_context.get('department', 'Unknown')}
- Query Complexity: {scenario.complexity.value}

ORIGINAL QUERY: "{query}"

AGENT RESPONSE: "{response_text}"

Evaluate the response quality and return ONLY a JSON object:
{{
    "helpfulness": <0-100 score for how helpful and useful the response is>,
    "clarity": <0-100 score for clarity, structure, and readability>,
    "completeness": <0-100 score for how comprehensive and complete the response is>,
    "professionalism": <0-100 score for appropriate tone and professionalism>,
    "accuracy": <0-100 score for factual accuracy and correctness>,
    "contextual_fit": <0-100 score for how well it fits the user's role and needs>
}}

Scoring scale:
- 90-100: Exceptional quality, exceeds expectations
- 75-89: High quality, meets expectations well  
- 60-74: Good quality, adequate for purpose
- 40-59: Fair quality, some issues present
- 20-39: Poor quality, significant problems
- 0-19: Very poor quality, fails basic requirements

Consider the user's expertise level and role when evaluating appropriateness."""

            deepseek_client = DeepSeekClient()
            
            evaluation_response = await deepseek_client.generate_response(
                prompt=evaluation_prompt,
                temperature=0.2,  # Very low temperature for consistent evaluation
                timeout_seconds=12
            )
            
            if not evaluation_response:
                logger.warning("LLM quality evaluation returned empty response")
                return self._default_llm_scores()
            
            try:
                scores = json.loads(evaluation_response.strip())
                return self._validate_llm_scores(scores)
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM quality JSON: {evaluation_response[:100]}...")
                return self._default_llm_scores()
                
        except Exception as e:
            logger.warning(f"LLM quality evaluation error: {e}")
            return self._default_llm_scores()
    
    def _default_llm_scores(self) -> Dict[str, float]:
        """Return default scores when LLM evaluation fails"""
        return {
            "helpfulness": 50.0,
            "clarity": 50.0,
            "completeness": 50.0,
            "professionalism": 50.0,
            "accuracy": 50.0,
            "contextual_fit": 50.0
        }
    
    def _validate_llm_scores(self, scores: Dict[str, Any]) -> Dict[str, float]:
        """Validate and constrain LLM scores to proper ranges"""
        required_keys = ["helpfulness", "clarity", "completeness", "professionalism", "accuracy", "contextual_fit"]
        validated_scores = {}
        
        for key in required_keys:
            if key in scores:
                try:
                    validated_scores[key] = max(0.0, min(100.0, float(scores[key])))
                except (ValueError, TypeError):
                    validated_scores[key] = 50.0
                    logger.warning(f"Invalid LLM score for {key}: {scores[key]}")
            else:
                validated_scores[key] = 50.0
                logger.warning(f"Missing LLM score key: {key}")
        
        return validated_scores
    
    def _score_source_integration(self, scenario: TestScenario, response: Dict[str, Any]) -> float:
        """Score source integration quality"""
        source_links = response.get("source_links", [])
        response_text = response.get("text", "")
        
        score = 50.0  # Base score
        
        # Has sources when expected
        if len(source_links) > 0:
            score += 30
        
        # Sources are organized (contains emoji headers)
        if any(emoji in response_text for emoji in ["📚", "🎫", "🌐", "💬"]):
            score += 20
        
        return min(score, 100.0)
    
    def _score_performance(self, scenario: TestScenario, response: Dict[str, Any], response_time: float) -> float:
        """Score performance metrics"""
        max_time = scenario.success_criteria.get("response_time_max", 60.0)
        
        if response_time <= max_time * 0.5:
            return 100.0
        elif response_time <= max_time * 0.75:
            return 80.0
        elif response_time <= max_time:
            return 60.0
        else:
            return 20.0
    
    def _score_followup_quality(self, scenario: TestScenario, response: Dict[str, Any]) -> float:
        """Score follow-up suggestion quality"""
        suggestions = response.get("suggestions", [])
        
        if len(suggestions) >= 3:
            return 100.0
        elif len(suggestions) >= 2:
            return 75.0
        elif len(suggestions) >= 1:
            return 50.0
        else:
            return 25.0

    def _analyze_response_details(self, scenario: TestScenario, response: Optional[Dict[str, Any]], 
                                 response_time: float) -> Dict[str, Any]:
        """Analyze detailed aspects of the response"""
        
        if not response:
            return {"status": "no_response"}
        
        return {
            "response_length": len(response.get("text", "")),
            "has_sources": len(response.get("source_links", [])) > 0,
            "has_suggestions": len(response.get("suggestions", [])) > 0,
            "confidence_level": response.get("confidence_level", "unknown"),
            "enhanced_mode": response.get("enhanced_mode", False),
            "response_time_category": "fast" if response_time < 10 else "medium" if response_time < 25 else "slow"
        }

    def _calculate_overall_metrics(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """Calculate overall performance metrics"""
        
        if not results:
            return {}
        
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        
        overall_scores = [r.scores.get("overall", 0) for r in results]
        response_times = [r.response_time for r in results]
        
        return {
            "success_rate": (success_count / total_count) * 100,
            "overall_score": sum(overall_scores) / len(overall_scores),
            "avg_response_time": sum(response_times) / len(response_times),
            "max_response_time": max(response_times),
            "min_response_time": min(response_times),
            "total_errors": sum(len(r.errors) for r in results)
        }

    def _generate_recommendations(self, results: List[EvaluationResult]) -> List[str]:
        """Generate improvement recommendations based on results"""
        
        recommendations = []
        
        # Analyze failure patterns
        failed_results = [r for r in results if not r.success]
        if len(failed_results) > len(results) * 0.2:  # More than 20% failure rate
            recommendations.append("High failure rate detected - review timeout handling and error recovery")
        
        # Analyze response time patterns
        slow_responses = [r for r in results if r.response_time > 30.0]
        if len(slow_responses) > len(results) * 0.3:  # More than 30% slow responses
            recommendations.append("Many slow responses - consider optimizing LLM timeouts and tool execution")
        
        # Analyze personality application
        low_personality_scores = [r for r in results if r.scores.get("personality_application", 100) < 70]
        if len(low_personality_scores) > len(results) * 0.4:
            recommendations.append("Personality application needs improvement - review contextual adaptation logic")
        
        return recommendations

    def _result_to_dict(self, result: EvaluationResult) -> Dict[str, Any]:
        """Convert EvaluationResult to dictionary for JSON serialization"""
        
        return {
            "scenario_id": result.scenario_id,
            "success": result.success,
            "scores": result.scores,
            "response_time": result.response_time,
            "response_preview": result.response_text[:200] + "..." if len(result.response_text) > 200 else result.response_text,
            "tools_used": result.tools_used,
            "errors": result.errors,
            "detailed_analysis": result.detailed_analysis
        }

    async def run_quick_test(self) -> Dict[str, Any]:
        """Run a quick subset of tests for rapid feedback"""
        
        quick_scenarios = ["simple_01", "moderate_01", "complex_01", "error_01"]
        return await self.run_evaluation(quick_scenarios)

    async def run_performance_test(self) -> Dict[str, Any]:
        """Run performance-focused tests"""
        
        performance_scenarios = ["performance_01", "moderate_01", "complex_01"]
        return await self.run_evaluation(performance_scenarios)

    async def run_personality_test(self) -> Dict[str, Any]:
        """Run personality-focused tests"""
        
        personality_scenarios = ["personality_01", "simple_01", "complex_02"]
        return await self.run_evaluation(personality_scenarios)

# CLI Interface
async def main():
    """CLI interface for running evaluations"""
    
    import sys
    
    # Check for LLM evaluation flag
    enable_llm = "--llm" in sys.argv or "--enable-llm" in sys.argv
    if enable_llm:
        sys.argv = [arg for arg in sys.argv if arg not in ["--llm", "--enable-llm"]]
    
    framework = AgentEvaluationFramework(enable_llm_evaluation=enable_llm)
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == "quick":
            result = await framework.run_quick_test()
        elif test_type == "performance":
            result = await framework.run_performance_test()
        elif test_type == "personality":
            result = await framework.run_personality_test()
        elif test_type == "full":
            result = await framework.run_evaluation()
        else:
            print("Usage: python evaluation_framework.py [quick|performance|personality|full] [--llm]")
            print("  --llm: Enable LLM-based evaluation enhancement (requires DEEPSEEK_API_KEY)")
            return
    else:
        # Default to quick test
        result = await framework.run_quick_test()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eval_method = "enhanced" if framework.enable_llm_evaluation else "standard"
    filename = f"evaluation_results_{eval_method}_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n📊 Evaluation results saved to: {filename}")
    print(f"Evaluation method: {'Enhanced (with LLM)' if framework.enable_llm_evaluation else 'Standard (Python-based)'}")

if __name__ == "__main__":
    print("🧪 Agent Evaluation Framework")
    print("Run with: python evaluation_framework.py [quick|performance|personality|full]")
    asyncio.run(main()) 