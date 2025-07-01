#!/usr/bin/env python3
"""
Script to fix all import paths after services reorganization
"""

import re
import os

# Mapping of old imports to new imports
IMPORT_MAPPINGS = {
    'from services.progress_tracker import': 'from services.processing.progress_tracker import',
    'from services.slack_connector import': 'from services.external_apis.slack_connector import',
    'from services.data_processor import': 'from services.processing.data_processor import',
    'from services.memory_service import': 'from services.core.memory_service import',
    'from services.document_ingestion import': 'from services.processing.document_ingestion import',
    'from services.channel_embedding_scheduler import': 'from services.processing.channel_embedding_scheduler import',
    'from services.embedding_service import': 'from services.data.embedding_service import',
    'from services.trace_manager import': 'from services.core.trace_manager import',
    'from services.token_manager import': 'from services.data.token_manager import',
    'from services.entity_store import': 'from services.data.entity_store import',
    'from services.notion_service import': 'from services.external_apis.notion_service import',
    'from services.enhanced_slack_connector import': 'from services.external_apis.enhanced_slack_connector import',
    'from services.ingestion_state_manager import': 'from services.processing.ingestion_state_manager import',
}

def fix_imports_in_file(filepath):
    """Fix imports in a single file"""
    if not os.path.exists(filepath):
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # Apply import mappings
    for old_import, new_import in IMPORT_MAPPINGS.items():
        if old_import in content:
            content = content.replace(old_import, new_import)
            changes_made += content.count(new_import) - original_content.count(new_import)
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed {changes_made} imports in {filepath}")
        return True
    
    return False

def main():
    # Files to fix
    files_to_fix = [
        'main.py',
        'workers/hourly_embedding_worker.py',
        'workers/bulk_channel_embedder.py',
        'workers/conversation_summarizer.py',
        'workers/entity_extractor.py',
        'workers/knowledge_update_worker.py'
    ]
    
    total_files_fixed = 0
    for filepath in files_to_fix:
        if fix_imports_in_file(filepath):
            total_files_fixed += 1
    
    print(f"\nCompleted: Fixed imports in {total_files_fixed} files")

if __name__ == "__main__":
    main()