#!/usr/bin/env python3
"""
Agent Test Runner - Comprehensive evaluation system for the orchestrator and client agent
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentTestRunner:
    """Test runner for comprehensive agent evaluation"""
    
    def __init__(self, enable_llm_evaluation: bool = None):
        self.test_scenarios = self._create_test_scenarios()
        
        # Auto-detect LLM evaluation availability
        if enable_llm_evaluation is None:
            self.enable_llm_evaluation = bool(os.getenv('DEEPSEEK_API_KEY'))
        else:
            self.enable_llm_evaluation = enable_llm_evaluation
            
        if self.enable_llm_evaluation:
            logger.info("🤖 LLM-based evaluation ENABLED - Enhanced quality assessment")
        else:
            logger.info("📝 Python-based evaluation only - Add DEEPSEEK_API_KEY for LLM evaluation")
    
    def _create_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create test scenarios covering different complexity levels and use cases"""
        
        return [
            {
                "id": "greeting_test",
                "name": "Basic Greeting Response",
                "query": "Hi there! How are you doing today?",
                "user_context": {
                    "first_name": "Sarah",
                    "title": "UX Designer", 
                    "department": "Design"
                },
                "channel_context": {
                    "is_dm": True,
                    "channel_name": "dm"
                },
                "expectations": {
                    "max_response_time": 15.0,
                    "min_response_length": 30,
                    "should_be_friendly": True,
                    "should_use_name": True
                }
            },
            
            {
                "id": "capability_inquiry",
                "name": "Capability Information Request",
                "query": "What can you help me with? What are your main capabilities?",
                "user_context": {
                    "first_name": "Mike",
                    "title": "Software Engineer",
                    "department": "Engineering"
                },
                "channel_context": {
                    "is_dm": False,
                    "channel_name": "general"
                },
                "expectations": {
                    "max_response_time": 15.0,
                    "should_list_capabilities": True,
                    "technical_depth": True
                }
            },
            
            {
                "id": "team_discussion_search",
                "name": "Team Discussion Search Query",
                "query": "What has the team been discussing about authentication systems recently?",
                "user_context": {
                    "first_name": "Alex",
                    "title": "Product Manager",
                    "department": "Product"
                },
                "channel_context": {
                    "is_dm": False,
                    "channel_name": "engineering"
                },
                "expectations": {
                    "max_response_time": 30.0,
                    "min_response_length": 100,
                    "expected_tools": ["vector_search"]
                }
            },
            
            {
                "id": "timeout_stress_test",
                "name": "Timeout Resilience Test",
                "query": "I need comprehensive analysis of UiPath Autopilot architecture, current AI automation trends, our team's recent discussions about AI implementation, existing project documentation, and strategic recommendations for our 2025 roadmap",
                "user_context": {
                    "first_name": "Test",
                    "title": "Engineer", 
                    "department": "Engineering"
                },
                "channel_context": {
                    "is_dm": False,
                    "channel_name": "test"
                },
                "expectations": {
                    "max_response_time": 60.0,
                    "should_not_timeout": True,
                    "min_response_length": 50
                }
            }
        ]
    
    async def run_tests(self, test_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run comprehensive tests on the agent system"""
        
        logger.info("🧪 STARTING AGENT EVALUATION")
        logger.info("=" * 50)
        
        # Select tests to run
        tests_to_run = []
        if test_ids:
            tests_to_run = [t for t in self.test_scenarios if t["id"] in test_ids]
        else:
            tests_to_run = self.test_scenarios
        
        logger.info(f"Running {len(tests_to_run)} test scenarios...")
        
        results = []
        overall_start_time = time.time()
        
        for test_scenario in tests_to_run:
            logger.info(f"\n🔍 Testing: {test_scenario['name']}")
            logger.info(f"Query: \"{test_scenario['query']}\"")
            
            result = await self._run_single_test(test_scenario)
            results.append(result)
            
            # Log immediate result
            status_emoji = "✅" if result["success"] else "❌"
            logger.info(f"{status_emoji} Result: {result['success']} | Score: {result['score']:.1f}/100 | Time: {result['response_time']:.1f}s")
            
            if result["errors"]:
                logger.warning(f"   Errors: {result['errors']}")
        
        # Calculate overall metrics
        overall_time = time.time() - overall_start_time
        overall_metrics = self._calculate_metrics(results)
        
        # Generate final report
        report = {
            "evaluation_timestamp": datetime.now().isoformat(),
            "total_tests": len(tests_to_run),
            "evaluation_time": overall_time,
            "overall_metrics": overall_metrics,
            "individual_results": results,
            "recommendations": self._generate_recommendations(results)
        }
        
        # Log summary
        logger.info(f"\n🎯 EVALUATION COMPLETE")
        logger.info(f"Overall Score: {overall_metrics['overall_score']:.1f}/100")
        logger.info(f"Success Rate: {overall_metrics['success_rate']:.1f}%")
        logger.info(f"Average Response Time: {overall_metrics['avg_response_time']:.1f}s")
        
        return report
    
    async def _run_single_test(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test scenario"""
        
        start_time = time.time()
        errors = []
        
        try:
            # Import here to avoid environment variable requirements during module loading
            from models.schemas import ProcessedMessage
            from agents.orchestrator_agent import OrchestratorAgent
            from services.core.memory_service import MemoryService
            
            # Initialize orchestrator
            memory_service = MemoryService()
            orchestrator = OrchestratorAgent(memory_service)
            
            # Create test message
            test_message = ProcessedMessage(
                text=scenario["query"],
                user_id="TEST_USER",
                user_name=scenario["user_context"].get("first_name", "TestUser"),
                user_email="test@example.com",
                user_display_name=scenario["user_context"].get("first_name", "Test User"),
                user_first_name=scenario["user_context"].get("first_name", "Test"),
                user_title=scenario["user_context"].get("title", ""),
                user_department=scenario["user_context"].get("department", ""),
                channel_id="TEST_CHANNEL",
                channel_name=scenario["channel_context"].get("channel_name", "test"),
                is_dm=scenario["channel_context"].get("is_dm", False),
                is_mention=True,
                thread_ts=None,
                message_ts=f"{int(time.time())}.000001"
            )
            
            # Execute the test
            response = await orchestrator.process_query(test_message)
            response_time = time.time() - start_time
            
            # Evaluate the response
            evaluation = await self._evaluate_response(scenario, response, response_time)
            
            return {
                "test_id": scenario["id"],
                "test_name": scenario["name"],
                "success": evaluation["success"],
                "score": evaluation["score"],
                "response_time": response_time,
                "response_preview": evaluation["response_preview"],
                "errors": errors,
                "detailed_analysis": evaluation["analysis"]
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            errors.append(f"Test execution failed: {str(e)}")
            
            return {
                "test_id": scenario["id"],
                "test_name": scenario["name"],
                "success": False,
                "score": 0.0,
                "response_time": response_time,
                "response_preview": "",
                "errors": errors,
                "detailed_analysis": {"exception": str(e)}
            }
    
    async def _evaluate_response(self, scenario: Dict[str, Any], response: Optional[Dict[str, Any]], 
                              response_time: float) -> Dict[str, Any]:
        """Evaluate the quality of a response against expectations"""
        
        expectations = scenario["expectations"]
        
        if not response:
            return {
                "success": False,
                "score": 0.0,
                "response_preview": "",
                "analysis": {"error": "No response received"}
            }
        
        response_text = response.get("text", "")
        
        # Get Python-based scores (0-100)
        python_scores = self._python_evaluate_response(scenario, response, response_time)
        
        # Get LLM-based scores if enabled (0-100)
        if self.enable_llm_evaluation and response_text:
            try:
                llm_scores = await self._llm_evaluate_response(scenario, response_text)
            except Exception as e:
                logger.warning(f"LLM evaluation failed: {e}")
                llm_scores = {"llm_helpfulness": 0, "llm_clarity": 0, "llm_professionalism": 0, "llm_completeness": 0}
        else:
            llm_scores = {"llm_helpfulness": 0, "llm_clarity": 0, "llm_professionalism": 0, "llm_completeness": 0}
        
        # Combine scores (70% Python-based, 30% LLM-based when available)
        if self.enable_llm_evaluation and any(score > 0 for score in llm_scores.values()):
            python_weight = 0.7
            llm_weight = 0.3
            avg_llm_score = sum(llm_scores.values()) / len(llm_scores)
            combined_score = (python_scores["total_score"] * python_weight) + (avg_llm_score * llm_weight)
        else:
            combined_score = python_scores["total_score"]
        
        # Success determination
        min_length = expectations.get("min_response_length", 20)
        max_time = expectations.get("max_response_time", 60.0)
        success = (
            response is not None and
            len(response_text) >= min_length and
            response_time <= max_time and
            combined_score >= 50  # Minimum score threshold
        )
        
        return {
            "success": success,
            "score": min(combined_score, 100.0),
            "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
            "analysis": {
                **python_scores["analysis"],
                **llm_scores,
                "evaluation_method": "hybrid" if self.enable_llm_evaluation else "python_only",
                "python_score": python_scores["total_score"],
                "llm_avg_score": sum(llm_scores.values()) / len(llm_scores) if llm_scores else 0
            }
        }
    
    def _python_evaluate_response(self, scenario: Dict[str, Any], response: Dict[str, Any], 
                                 response_time: float) -> Dict[str, Any]:
        """Python-based evaluation using programmatic criteria"""
        
        expectations = scenario["expectations"]
        response_text = response.get("text", "")
        score = 0.0
        analysis = {}
        
        # Basic response checks
        if response_text:
            score += 20  # Base score for having a response
        
        # Length check
        min_length = expectations.get("min_response_length", 20)
        if len(response_text) >= min_length:
            score += 15
            analysis["length_check"] = "passed"
        else:
            analysis["length_check"] = f"failed - {len(response_text)} < {min_length}"
        
        # Response time check
        max_time = expectations.get("max_response_time", 60.0)
        if response_time <= max_time:
            score += 15
            analysis["timing_check"] = "passed"
        else:
            analysis["timing_check"] = f"failed - {response_time:.1f}s > {max_time}s"
        
        # No error messages
        if not any(phrase in response_text.lower() for phrase in ["technical difficulties", "error occurred", "sorry"]):
            score += 20
            analysis["error_check"] = "passed"
        else:
            analysis["error_check"] = "failed - contains error messages"
        
        # Personality checks
        if expectations.get("should_use_name") and scenario["user_context"].get("first_name"):
            if scenario["user_context"]["first_name"] in response_text:
                score += 10
                analysis["name_usage"] = "passed"
            else:
                analysis["name_usage"] = "failed"
        
        # Technical depth for technical users
        if expectations.get("technical_depth"):
            if any(word in response_text.lower() for word in ["technical", "implementation", "architecture", "system"]):
                score += 10
                analysis["technical_depth"] = "passed"
            else:
                analysis["technical_depth"] = "not detected"
        
        # Friendly tone
        if expectations.get("should_be_friendly"):
            if any(word in response_text.lower() for word in ["hi", "hello", "help", "happy", "great"]):
                score += 10
                analysis["friendly_tone"] = "detected"
        
        return {
            "total_score": min(score, 100.0),
            "analysis": analysis
        }
    
    async def _llm_evaluate_response(self, scenario: Dict[str, Any], response_text: str) -> Dict[str, float]:
        """LLM-based evaluation for nuanced quality assessment"""
        
        try:
            # Import DeepSeek client
            sys.path.append(str(Path(__file__).parent.parent))
            from utils.deepseek_client import DeepSeekClient
            
            # Create evaluation prompt
            user_context = scenario["user_context"]
            query = scenario["query"]
            
            evaluation_prompt = f"""You are an expert evaluator of AI agent responses. Rate this agent response on the following criteria using a scale of 0-100:

USER CONTEXT:
- Name: {user_context.get('first_name', 'Unknown')}
- Title: {user_context.get('title', 'Unknown')}
- Department: {user_context.get('department', 'Unknown')}

ORIGINAL QUERY: "{query}"

AGENT RESPONSE: "{response_text}"

Please evaluate and return ONLY a JSON object with these exact keys:
{{
    "llm_helpfulness": <0-100 score for how helpful the response is>,
    "llm_clarity": <0-100 score for how clear and well-structured the response is>,
    "llm_professionalism": <0-100 score for appropriate tone and professionalism>,
    "llm_completeness": <0-100 score for how complete and comprehensive the response is>
}}

Scoring guidelines:
- 90-100: Excellent, exceeds expectations
- 70-89: Good, meets expectations well
- 50-69: Adequate, meets basic expectations
- 30-49: Poor, below expectations
- 0-29: Very poor, fails to meet expectations

Consider the user's role and context when evaluating appropriateness."""

            # Get LLM evaluation
            deepseek_client = DeepSeekClient()
            
            evaluation_response = await deepseek_client.generate_response(
                prompt=evaluation_prompt,
                temperature=0.3,  # Lower temperature for consistent evaluation
                timeout_seconds=10
            )
            
            if not evaluation_response:
                logger.warning("LLM evaluation returned empty response")
                return {"llm_helpfulness": 0, "llm_clarity": 0, "llm_professionalism": 0, "llm_completeness": 0}
            
            # Parse JSON response
            try:
                scores = json.loads(evaluation_response.strip())
                
                # Validate and constrain scores
                required_keys = ["llm_helpfulness", "llm_clarity", "llm_professionalism", "llm_completeness"]
                validated_scores = {}
                
                for key in required_keys:
                    if key in scores:
                        # Ensure score is between 0-100
                        validated_scores[key] = max(0, min(100, float(scores[key])))
                    else:
                        validated_scores[key] = 0
                        logger.warning(f"Missing LLM evaluation key: {key}")
                
                return validated_scores
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM evaluation JSON: {evaluation_response}")
                return {"llm_helpfulness": 0, "llm_clarity": 0, "llm_professionalism": 0, "llm_completeness": 0}
                
        except Exception as e:
            logger.warning(f"LLM evaluation error: {e}")
            return {"llm_helpfulness": 0, "llm_clarity": 0, "llm_professionalism": 0, "llm_completeness": 0}
    
    def _calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate overall performance metrics"""
        
        if not results:
            return {}
        
        success_count = sum(1 for r in results if r["success"])
        total_tests = len(results)
        
        scores = [r["score"] for r in results]
        response_times = [r["response_time"] for r in results]
        error_count = sum(len(r["errors"]) for r in results)
        
        return {
            "success_rate": (success_count / total_tests) * 100,
            "overall_score": sum(scores) / len(scores),
            "avg_response_time": sum(response_times) / len(response_times),
            "max_response_time": max(response_times),
            "min_response_time": min(response_times),
            "total_errors": error_count
        }
    
    def _generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate improvement recommendations based on test results"""
        
        recommendations = []
        
        # Analyze failure patterns
        failed_tests = [r for r in results if not r["success"]]
        if len(failed_tests) > len(results) * 0.2:
            recommendations.append("High failure rate detected - review error handling and timeout management")
        
        # Analyze response times
        slow_tests = [r for r in results if r["response_time"] > 30.0]
        if len(slow_tests) > len(results) * 0.3:
            recommendations.append("Many slow responses - consider optimizing LLM timeouts and tool execution")
        
        # Analyze scores
        low_score_tests = [r for r in results if r["score"] < 70.0]
        if len(low_score_tests) > len(results) * 0.4:
            recommendations.append("Many low-quality responses - review prompt engineering and response generation")
        
        return recommendations

async def main():
    """CLI interface for running agent tests"""
    
    import sys
    
    # Check for LLM evaluation flag
    enable_llm = "--llm" in sys.argv or "--enable-llm" in sys.argv
    if enable_llm:
        sys.argv = [arg for arg in sys.argv if arg not in ["--llm", "--enable-llm"]]
    
    runner = AgentTestRunner(enable_llm_evaluation=enable_llm)
    
    test_type = sys.argv[1] if len(sys.argv) > 1 else "quick"
    
    if test_type == "quick":
        result = await runner.run_tests(["greeting_test", "team_discussion_search"])
    elif test_type == "full":
        result = await runner.run_tests()
    else:
        print("Usage: python test_runner.py [quick|full] [--llm]")
        print("  --llm: Enable LLM-based evaluation (requires DEEPSEEK_API_KEY)")
        return
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eval_method = "hybrid" if runner.enable_llm_evaluation else "python"
    filename = f"test_results_{test_type}_{eval_method}_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n📊 Test results saved to: {filename}")
    
    # Print summary
    metrics = result["overall_metrics"]
    print(f"\n🎯 TEST SUMMARY:")
    print(f"   Overall Score: {metrics['overall_score']:.1f}/100")
    print(f"   Success Rate: {metrics['success_rate']:.1f}%")
    print(f"   Average Response Time: {metrics['avg_response_time']:.1f}s")
    print(f"   Evaluation Method: {'Hybrid (Python + LLM)' if runner.enable_llm_evaluation else 'Python-based only'}")
    
    if result["recommendations"]:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in result["recommendations"]:
            print(f"   • {rec}")

if __name__ == "__main__":
    asyncio.run(main())
