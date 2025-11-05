#!/bin/bash
cd /home/kavia/workspace/code-generation/uttar-pradesh-tourism-project-monitoring-system-219537-219546/upstdc_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

