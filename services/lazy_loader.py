"""
Lazy Loading Service for Heavy Dependencies

Implements lazy loading patterns to reduce startup time and memory usage
by loading heavy modules only when needed.
"""

import logging
import time
from typing import Any, Optional, Dict, Callable
import threading

logger = logging.getLogger(__name__)

class LazyLoader:
    """Lazy loader for heavy modules and dependencies"""
    
    def __init__(self):
        self._loaded_modules: Dict[str, Any] = {}
        self._loading_locks: Dict[str, threading.Lock] = {}
        self._load_times: Dict[str, float] = {}
        
    def get_module(self, module_name: str, loader_func: Callable = None) -> Any:
        """Get module with lazy loading"""
        if module_name in self._loaded_modules:
            return self._loaded_modules[module_name]
        
        # Ensure thread safety during loading
        if module_name not in self._loading_locks:
            self._loading_locks[module_name] = threading.Lock()
        
        with self._loading_locks[module_name]:
            # Double-check pattern
            if module_name in self._loaded_modules:
                return self._loaded_modules[module_name]
            
            start_time = time.time()
            
            try:
                if loader_func:
                    module = loader_func()
                else:
                    module = __import__(module_name)
                
                self._loaded_modules[module_name] = module
                self._load_times[module_name] = time.time() - start_time
                
                logger.debug(f"Lazy loaded {module_name} in {self._load_times[module_name]:.3f}s")
                return module
                
            except Exception as e:
                logger.warning(f"Failed to lazy load {module_name}: {e}")
                return None
    
    def preload_critical_modules(self):
        """Preload critical modules in background"""
        def load_google_genai():
            try:
                from google import genai
                return genai
            except ImportError:
                return None
        
        def load_sentence_transformers():
            try:
                from sentence_transformers import SentenceTransformer
                return SentenceTransformer
            except ImportError:
                return None
        
        def load_pinecone():
            try:
                import pinecone
                return pinecone
            except ImportError:
                return None
        
        # Load modules in background thread
        modules_to_load = [
            ('google.genai', load_google_genai),
            ('sentence_transformers', load_sentence_transformers),
            ('pinecone', load_pinecone)
        ]
        threading.Thread(
            target=self._background_preload,
            args=(modules_to_load,),
            daemon=True
        ).start()
    
    def _background_preload(self, modules_to_load):
        """Background preloading of modules"""
        for module_name, loader_func in modules_to_load:
            try:
                self.get_module(module_name, loader_func)
            except Exception as e:
                logger.debug(f"Background preload failed for {module_name}: {e}")
    
    def get_load_stats(self) -> Dict[str, Any]:
        """Get loading statistics"""
        return {
            "loaded_modules": list(self._loaded_modules.keys()),
            "load_times": self._load_times,
            "total_modules": len(self._loaded_modules)
        }

# Global lazy loader instance
lazy_loader = LazyLoader()