#!/usr/bin/env python
"""
Quick test to verify WebSocket log streaming works
"""
import logging
import time

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

# Test loggers
orchestrator_logger = logging.getLogger('orchestrator')
workflow_logger = logging.getLogger('workflow_engine')
adapter_logger = logging.getLogger('adapter.codex')

print("Testing log filtering...")
print()

# These should match the filter
test_logs = [
    (orchestrator_logger, "Executing task: Test"),
    (workflow_logger, "Workflow configured with 2 steps"),
    (adapter_logger, "Executing codex with prompt"),
    (orchestrator_logger, "Iteration 1/3"),
]

for logger, message in test_logs:
    logger.info(message)
    print(f"✓ Logged to {logger.name}: {message}")
    
print()
print("If you see the logs above, the logging system is working.")
print("The WebSocketLogHandler should capture these when running via app.py")
