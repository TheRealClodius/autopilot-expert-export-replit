#!/usr/bin/env python3
"""
Deployment Environment Analysis

Deep analysis of environment differences between local working setup
and deployment build that could cause "execution error" failures.
"""

import asyncio
import os
import sys
import json
import httpx
import time
import platform
import psutil
import socket
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings

class DeploymentEnvironmentAnalyzer:
    """Comprehensive analysis of deployment environment differences"""
    
    def __init__(self):
        self.analysis_results = {
            "timestamp": time.time(),
            "system_environment": {},
            "network_environment": {},
            "process_environment": {},
            "resource_constraints": {},
            "build_vs_runtime": {},
            "dependency_differences": {},
            "deployment_specific": {},
            "critical_differences": [],
            "recommendations": []
        }
    
    async def analyze_deployment_differences(self):
        """Perform comprehensive deployment environment analysis"""
        print("🔍 DEPLOYMENT ENVIRONMENT ANALYSIS")
        print("=" * 60)
        
        await self._analyze_system_environment()
        await self._analyze_network_environment()
        await self._analyze_process_environment()
        await self._analyze_resource_constraints()
        await self._analyze_build_vs_runtime()
        await self._analyze_dependency_differences()
        await self._analyze_deployment_specific()
        
        self._identify_critical_differences()
        self._generate_recommendations()
        self._print_analysis_results()
        
        return self.analysis_results
    
    async def _analyze_system_environment(self):
        """Analyze system-level environment differences"""
        print("\n🖥️ System Environment Analysis")
        print("-" * 40)
        
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "current_user": os.getenv("USER", "unknown"),
            "home_directory": os.getenv("HOME", "unknown"),
            "shell": os.getenv("SHELL", "unknown"),
            "path_dirs": len(os.getenv("PATH", "").split(":")),
            "python_path": sys.executable,
            "working_directory": os.getcwd(),
            "temp_directory": os.getenv("TMPDIR", "/tmp"),
            "timezone": os.getenv("TZ", "unknown")
        }
        
        # Check for containerization indicators
        containerization_indicators = {
            "docker_env": os.path.exists("/.dockerenv"),
            "kubernetes_env": os.getenv("KUBERNETES_SERVICE_HOST") is not None,
            "replit_env": os.getenv("REPL_ID") is not None,
            "cloud_run_env": os.getenv("K_SERVICE") is not None,
            "container_runtime": os.getenv("container") is not None
        }
        
        print(f"  Platform: {system_info['platform']}")
        print(f"  Python: {system_info['python_version']}")
        print(f"  Architecture: {system_info['architecture']}")
        print(f"  Hostname: {system_info['hostname']}")
        print(f"  User: {system_info['current_user']}")
        print(f"  Working Dir: {system_info['working_directory']}")
        
        for indicator, present in containerization_indicators.items():
            print(f"  {indicator}: {'✅ Yes' if present else '❌ No'}")
        
        self.analysis_results["system_environment"] = {
            "system_info": system_info,
            "containerization": containerization_indicators
        }
        
        # Identify potential issues
        if containerization_indicators["docker_env"]:
            self.analysis_results["critical_differences"].append("Running in Docker container - may have network isolation")
        
        if containerization_indicators["cloud_run_env"]:
            self.analysis_results["critical_differences"].append("Cloud Run environment - ephemeral filesystem and networking restrictions")
    
    async def _analyze_network_environment(self):
        """Analyze network environment and connectivity patterns"""
        print("\n🌐 Network Environment Analysis")
        print("-" * 40)
        
        network_info = {
            "localhost_resolution": None,
            "external_connectivity": {},
            "port_accessibility": {},
            "dns_resolution": {},
            "proxy_settings": {
                "http_proxy": os.getenv("HTTP_PROXY"),
                "https_proxy": os.getenv("HTTPS_PROXY"),
                "no_proxy": os.getenv("NO_PROXY")
            }
        }
        
        # Test localhost resolution
        try:
            localhost_ip = socket.gethostbyname("localhost")
            network_info["localhost_resolution"] = localhost_ip
            print(f"  Localhost resolves to: {localhost_ip}")
        except Exception as e:
            network_info["localhost_resolution"] = f"Error: {str(e)}"
            print(f"  Localhost resolution: ❌ Error: {str(e)}")
            self.analysis_results["critical_differences"].append("Localhost resolution failure")
        
        # Test external connectivity
        external_hosts = [
            ("google.com", 80),
            ("uipath.atlassian.net", 443),
            ("api.openai.com", 443)
        ]
        
        for host, port in external_hosts:
            try:
                with socket.create_connection((host, port), timeout=5):
                    network_info["external_connectivity"][f"{host}:{port}"] = "accessible"
                    print(f"  {host}:{port}: ✅ Accessible")
            except Exception as e:
                network_info["external_connectivity"][f"{host}:{port}"] = f"Error: {str(e)}"
                print(f"  {host}:{port}: ❌ Error: {str(e)}")
                if "uipath.atlassian.net" in host:
                    self.analysis_results["critical_differences"].append("Atlassian API not accessible")
        
        # Test local port accessibility
        local_ports = [5000, 8001, 8080, 3000]
        for port in local_ports:
            try:
                with socket.create_connection(("localhost", port), timeout=2):
                    network_info["port_accessibility"][str(port)] = "accessible"
                    print(f"  Port {port}: ✅ Accessible")
            except Exception as e:
                network_info["port_accessibility"][str(port)] = f"Error: {str(e)}"
                print(f"  Port {port}: ❌ Not accessible")
                if port == 8001:
                    self.analysis_results["critical_differences"].append("MCP server port 8001 not accessible")
        
        # Test DNS resolution
        dns_hosts = ["localhost", "uipath.atlassian.net", "api.openai.com"]
        for host in dns_hosts:
            try:
                ip = socket.gethostbyname(host)
                network_info["dns_resolution"][host] = ip
                print(f"  DNS {host}: ✅ {ip}")
            except Exception as e:
                network_info["dns_resolution"][host] = f"Error: {str(e)}"
                print(f"  DNS {host}: ❌ Error: {str(e)}")
        
        # Check proxy settings
        for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"]:
            value = os.getenv(proxy_var)
            if value:
                print(f"  {proxy_var}: {value}")
                if proxy_var in ["HTTP_PROXY", "HTTPS_PROXY"]:
                    self.analysis_results["critical_differences"].append(f"Proxy configured: {proxy_var}={value}")
        
        self.analysis_results["network_environment"] = network_info
    
    async def _analyze_process_environment(self):
        """Analyze process-level environment and permissions"""
        print("\n⚙️ Process Environment Analysis")
        print("-" * 40)
        
        try:
            process = psutil.Process()
            process_info = {
                "pid": process.pid,
                "ppid": process.ppid(),
                "name": process.name(),
                "username": process.username(),
                "cwd": process.cwd(),
                "memory_info": process.memory_info()._asdict(),
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections()),
                "create_time": process.create_time()
            }
            
            print(f"  Process ID: {process_info['pid']}")
            print(f"  Parent PID: {process_info['ppid']}")
            print(f"  Username: {process_info['username']}")
            print(f"  Memory RSS: {process_info['memory_info']['rss'] / 1024 / 1024:.1f} MB")
            print(f"  Open files: {process_info['open_files']}")
            print(f"  Network connections: {process_info['connections']}")
            
        except Exception as e:
            process_info = {"error": str(e)}
            print(f"  Process analysis failed: {str(e)}")
        
        # Check file system permissions
        file_permissions = {}
        test_paths = [
            ".",
            "./config.py",
            "./tools/atlassian_tool.py",
            "./prompts.yaml",
            "/tmp"
        ]
        
        for path in test_paths:
            try:
                stat_info = os.stat(path)
                file_permissions[path] = {
                    "exists": True,
                    "readable": os.access(path, os.R_OK),
                    "writable": os.access(path, os.W_OK),
                    "executable": os.access(path, os.X_OK),
                    "mode": oct(stat_info.st_mode)[-3:]
                }
                perms = file_permissions[path]
                print(f"  {path}: {'r' if perms['readable'] else '-'}{'w' if perms['writable'] else '-'}{'x' if perms['executable'] else '-'} ({perms['mode']})")
            except Exception as e:
                file_permissions[path] = {"exists": False, "error": str(e)}
                print(f"  {path}: ❌ Error: {str(e)}")
                if path in ["./config.py", "./tools/atlassian_tool.py"]:
                    self.analysis_results["critical_differences"].append(f"Critical file not accessible: {path}")
        
        self.analysis_results["process_environment"] = {
            "process_info": process_info,
            "file_permissions": file_permissions
        }
    
    async def _analyze_resource_constraints(self):
        """Analyze resource constraints and limits"""
        print("\n📊 Resource Constraints Analysis")
        print("-" * 40)
        
        try:
            # System memory
            memory = psutil.virtual_memory()
            print(f"  Total Memory: {memory.total / 1024 / 1024 / 1024:.1f} GB")
            print(f"  Available Memory: {memory.available / 1024 / 1024 / 1024:.1f} GB")
            print(f"  Memory Usage: {memory.percent}%")
            
            # CPU information
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=1)
            print(f"  CPU Cores: {cpu_count}")
            print(f"  CPU Usage: {cpu_percent}%")
            
            # Disk space
            disk = psutil.disk_usage('/')
            print(f"  Disk Total: {disk.total / 1024 / 1024 / 1024:.1f} GB")
            print(f"  Disk Free: {disk.free / 1024 / 1024 / 1024:.1f} GB")
            print(f"  Disk Usage: {(disk.used / disk.total) * 100:.1f}%")
            
            resource_info = {
                "memory": memory._asdict(),
                "cpu_count": cpu_count,
                "cpu_percent": cpu_percent,
                "disk": disk._asdict()
            }
            
            # Check for resource constraints
            if memory.percent > 80:
                self.analysis_results["critical_differences"].append(f"High memory usage: {memory.percent}%")
            
            if cpu_percent > 80:
                self.analysis_results["critical_differences"].append(f"High CPU usage: {cpu_percent}%")
            
            if (disk.used / disk.total) * 100 > 90:
                self.analysis_results["critical_differences"].append(f"Low disk space: {(disk.used / disk.total) * 100:.1f}%")
            
        except Exception as e:
            resource_info = {"error": str(e)}
            print(f"  Resource analysis failed: {str(e)}")
        
        # Check ulimits (Unix/Linux only)
        ulimit_info = {}
        if hasattr(os, 'getrlimit'):
            try:
                import resource
                ulimit_info = {
                    "max_open_files": resource.getrlimit(resource.RLIMIT_NOFILE),
                    "max_processes": resource.getrlimit(resource.RLIMIT_NPROC),
                    "max_memory": resource.getrlimit(resource.RLIMIT_AS)
                }
                print(f"  Max open files: {ulimit_info['max_open_files'][0]}")
                print(f"  Max processes: {ulimit_info['max_processes'][0]}")
            except Exception as e:
                ulimit_info = {"error": str(e)}
        
        self.analysis_results["resource_constraints"] = {
            "system_resources": resource_info,
            "ulimits": ulimit_info
        }
    
    async def _analyze_build_vs_runtime(self):
        """Analyze differences between build time and runtime environments"""
        print("\n🏗️ Build vs Runtime Environment Analysis")
        print("-" * 40)
        
        build_indicators = {
            "build_environment": os.getenv("BUILD_ENV"),
            "ci_environment": os.getenv("CI"),
            "github_actions": os.getenv("GITHUB_ACTIONS"),
            "replit_deployment": os.getenv("REPL_DEPLOYMENT"),
            "production_env": os.getenv("NODE_ENV") == "production",
            "debug_mode": os.getenv("DEBUG", "").lower() in ["true", "1"],
            "log_level": os.getenv("LOG_LEVEL", "INFO")
        }
        
        # Check for deployment-specific environment variables
        deployment_vars = [
            "PORT", "HOST", "K_SERVICE", "K_REVISION", "K_CONFIGURATION",
            "GOOGLE_CLOUD_PROJECT", "GAE_SERVICE", "REPL_ID", "REPL_SLUG"
        ]
        
        deployment_env = {}
        for var in deployment_vars:
            value = os.getenv(var)
            if value:
                deployment_env[var] = value
                print(f"  {var}: {value}")
        
        # Check if we're in a build environment
        is_build_time = any([
            build_indicators["ci_environment"],
            build_indicators["github_actions"],
            build_indicators["build_environment"]
        ])
        
        if is_build_time:
            print("  Environment: ⚠️ Build/CI detected")
            self.analysis_results["critical_differences"].append("Running in build/CI environment")
        else:
            print("  Environment: ✅ Runtime")
        
        # Check for read-only filesystem (common in some deployments)
        try:
            test_file = "/tmp/write_test"
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            filesystem_writable = True
            print("  Filesystem: ✅ Writable")
        except Exception as e:
            filesystem_writable = False
            print(f"  Filesystem: ❌ Read-only or restricted: {str(e)}")
            self.analysis_results["critical_differences"].append("Filesystem not writable")
        
        self.analysis_results["build_vs_runtime"] = {
            "build_indicators": build_indicators,
            "deployment_env": deployment_env,
            "is_build_time": is_build_time,
            "filesystem_writable": filesystem_writable
        }
    
    async def _analyze_dependency_differences(self):
        """Analyze differences in dependencies and imports"""
        print("\n📦 Dependency Analysis")
        print("-" * 40)
        
        # Check critical imports
        critical_imports = [
            "fastapi", "uvicorn", "httpx", "asyncio", "json", "os", "sys",
            "pydantic", "google.generativeai", "pinecone", "slack_sdk",
            "atlassian", "mcp"
        ]
        
        import_results = {}
        for module in critical_imports:
            try:
                __import__(module)
                import_results[module] = "available"
                print(f"  {module}: ✅ Available")
            except ImportError as e:
                import_results[module] = f"ImportError: {str(e)}"
                print(f"  {module}: ❌ ImportError: {str(e)}")
                self.analysis_results["critical_differences"].append(f"Missing dependency: {module}")
            except Exception as e:
                import_results[module] = f"Error: {str(e)}"
                print(f"  {module}: ❌ Error: {str(e)}")
        
        # Check Python path
        python_path_dirs = sys.path
        print(f"  Python path entries: {len(python_path_dirs)}")
        
        # Check for virtual environment
        venv_indicators = {
            "virtual_env": os.getenv("VIRTUAL_ENV"),
            "conda_env": os.getenv("CONDA_DEFAULT_ENV"),
            "pipenv": os.getenv("PIPENV_ACTIVE"),
            "poetry_env": os.getenv("POETRY_ACTIVE")
        }
        
        for indicator, value in venv_indicators.items():
            if value:
                print(f"  {indicator}: {value}")
        
        self.analysis_results["dependency_differences"] = {
            "import_results": import_results,
            "python_path_count": len(python_path_dirs),
            "virtual_env": venv_indicators
        }
    
    async def _analyze_deployment_specific(self):
        """Analyze deployment-specific configurations and restrictions"""
        print("\n🚀 Deployment-Specific Analysis")
        print("-" * 40)
        
        # Check for common deployment restrictions
        deployment_checks = {}
        
        # Test MCP server accessibility in deployment
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8001/healthz")
                deployment_checks["mcp_server_local"] = {
                    "accessible": True,
                    "status_code": response.status_code,
                    "response_time": "< 5s"
                }
                print(f"  MCP server (localhost:8001): ✅ Accessible ({response.status_code})")
        except Exception as e:
            deployment_checks["mcp_server_local"] = {
                "accessible": False,
                "error": str(e)
            }
            print(f"  MCP server (localhost:8001): ❌ Not accessible: {str(e)}")
            self.analysis_results["critical_differences"].append("MCP server not accessible on localhost:8001")
        
        # Test with different localhost alternatives
        localhost_alternatives = ["127.0.0.1", "0.0.0.0", socket.gethostname()]
        for host in localhost_alternatives:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"http://{host}:8001/healthz")
                    deployment_checks[f"mcp_server_{host}"] = {
                        "accessible": True,
                        "status_code": response.status_code
                    }
                    print(f"  MCP server ({host}:8001): ✅ Accessible ({response.status_code})")
            except Exception as e:
                deployment_checks[f"mcp_server_{host}"] = {
                    "accessible": False,
                    "error": str(e)
                }
                print(f"  MCP server ({host}:8001): ❌ Not accessible")
        
        # Test Atlassian API accessibility with deployment network
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://uipath.atlassian.net/")
                deployment_checks["atlassian_api"] = {
                    "accessible": True,
                    "status_code": response.status_code
                }
                print(f"  Atlassian API: ✅ Accessible ({response.status_code})")
        except Exception as e:
            deployment_checks["atlassian_api"] = {
                "accessible": False,
                "error": str(e)
            }
            print(f"  Atlassian API: ❌ Not accessible: {str(e)}")
            self.analysis_results["critical_differences"].append("Atlassian API not accessible from deployment")
        
        # Check environment variable accessibility in deployment
        env_var_check = {}
        required_vars = [
            "ATLASSIAN_JIRA_URL", "ATLASSIAN_JIRA_USERNAME", "ATLASSIAN_JIRA_TOKEN",
            "ATLASSIAN_CONFLUENCE_URL", "ATLASSIAN_CONFLUENCE_USERNAME", "ATLASSIAN_CONFLUENCE_TOKEN"
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            env_var_check[var] = {
                "present": bool(value),
                "length": len(value) if value else 0
            }
            status = "✅ Present" if value else "❌ Missing"
            print(f"  {var}: {status}")
            
            if not value:
                self.analysis_results["critical_differences"].append(f"Missing environment variable in deployment: {var}")
        
        self.analysis_results["deployment_specific"] = {
            "deployment_checks": deployment_checks,
            "environment_variables": env_var_check
        }
    
    def _identify_critical_differences(self):
        """Identify the most critical differences that could cause failures"""
        print("\n⚠️ Critical Differences Identified")
        print("-" * 40)
        
        if not self.analysis_results["critical_differences"]:
            print("  ✅ No critical differences detected")
            return
        
        # Categorize differences by severity
        severity_map = {
            "high": [],
            "medium": [],
            "low": []
        }
        
        high_severity_patterns = [
            "MCP server not accessible",
            "Atlassian API not accessible", 
            "Missing environment variable",
            "Critical file not accessible",
            "Missing dependency"
        ]
        
        medium_severity_patterns = [
            "High memory usage",
            "High CPU usage",
            "Proxy configured",
            "Build/CI environment"
        ]
        
        for difference in self.analysis_results["critical_differences"]:
            categorized = False
            for pattern in high_severity_patterns:
                if pattern.lower() in difference.lower():
                    severity_map["high"].append(difference)
                    categorized = True
                    break
            
            if not categorized:
                for pattern in medium_severity_patterns:
                    if pattern.lower() in difference.lower():
                        severity_map["medium"].append(difference)
                        categorized = True
                        break
            
            if not categorized:
                severity_map["low"].append(difference)
        
        for severity, differences in severity_map.items():
            if differences:
                print(f"\n  {severity.upper()} SEVERITY:")
                for diff in differences:
                    print(f"    - {diff}")
        
        self.analysis_results["critical_differences_categorized"] = severity_map
    
    def _generate_recommendations(self):
        """Generate specific recommendations based on identified differences"""
        recommendations = []
        
        high_severity = self.analysis_results.get("critical_differences_categorized", {}).get("high", [])
        
        if any("MCP server not accessible" in diff for diff in high_severity):
            recommendations.extend([
                "Ensure MCP Atlassian Server workflow is started before FastAPI Server",
                "Verify MCP server binds to 0.0.0.0:8001 not localhost:8001",
                "Check if deployment environment blocks inter-process communication",
                "Add startup coordination with health check polling"
            ])
        
        if any("Missing environment variable" in diff for diff in high_severity):
            recommendations.extend([
                "Verify all 6 Atlassian environment variables are set in deployment",
                "Check if deployment environment strips or modifies environment variables",
                "Ensure secrets are properly injected into deployment container"
            ])
        
        if any("Atlassian API not accessible" in diff for diff in high_severity):
            recommendations.extend([
                "Check if deployment environment has outbound internet restrictions",
                "Verify firewall allows HTTPS traffic to *.atlassian.net",
                "Test with explicit proxy configuration if corporate network"
            ])
        
        if any("Proxy configured" in diff for diff in self.analysis_results["critical_differences"]):
            recommendations.extend([
                "Configure httpx client to use proxy settings",
                "Add proxy authentication if required",
                "Whitelist localhost traffic from proxy"
            ])
        
        if any("Build/CI environment" in diff for diff in self.analysis_results["critical_differences"]):
            recommendations.extend([
                "Ensure deployment runs in runtime mode, not build mode",
                "Check if services are started during build vs runtime phase"
            ])
        
        # Default recommendations if no specific issues found
        if not recommendations:
            recommendations.extend([
                "Add comprehensive startup logging to identify timing issues",
                "Implement retry logic for MCP server connection during startup",
                "Monitor resource usage during deployment startup",
                "Test with deployment-specific network configuration"
            ])
        
        self.analysis_results["recommendations"] = recommendations
    
    def _print_analysis_results(self):
        """Print summary of analysis results"""
        print("\n" + "=" * 60)
        print("📋 DEPLOYMENT ENVIRONMENT ANALYSIS SUMMARY")
        print("=" * 60)
        
        critical_count = len(self.analysis_results["critical_differences"])
        recommendation_count = len(self.analysis_results["recommendations"])
        
        print(f"\n🔍 Analysis Complete:")
        print(f"  - Critical differences found: {critical_count}")
        print(f"  - Recommendations generated: {recommendation_count}")
        
        if critical_count > 0:
            print(f"\n⚠️ Critical Issues Detected ({critical_count}):")
            for i, diff in enumerate(self.analysis_results["critical_differences"][:5], 1):
                print(f"  {i}. {diff}")
            if critical_count > 5:
                print(f"  ... and {critical_count - 5} more")
        else:
            print(f"\n✅ No critical environment differences detected")
        
        print(f"\n💡 Top Recommendations:")
        for i, rec in enumerate(self.analysis_results["recommendations"][:3], 1):
            print(f"  {i}. {rec}")
        
        print(f"\n📊 Full analysis saved to deployment_environment_analysis.json")

async def main():
    """Run deployment environment analysis"""
    analyzer = DeploymentEnvironmentAnalyzer()
    results = await analyzer.analyze_deployment_differences()
    
    # Save results to file
    with open("deployment_environment_analysis.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    return len(results["critical_differences"]) == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)