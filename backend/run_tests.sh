#!/bin/bash
# 测试执行脚本（支持按模块分批和快速冒烟测试）

cd /root/.openclaw/workspace/sentiment-analysis/backend
source venv/bin/activate
export PYTHONPATH=/root/.openclaw/workspace/sentiment-analysis:/root/.openclaw/workspace/sentiment-analysis/backend:$PYTHONPATH

# 解析参数
MODULE=""
SMOKE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --module=*)
      MODULE="${1#*=}"
      shift
      ;;
    --smoke)
      SMOKE=true
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [ "$SMOKE" = true ]; then
  echo "🚀 Running smoke tests (5 core endpoints)..."
  python tests/test_smoke.py
elif [ -n "$MODULE" ]; then
  echo "🚀 Running tests for module: $MODULE"
  python tests/test_full_validation.py --module="$MODULE"
else
  echo "🚀 Running full validation tests (all modules)..."
  echo "⚠️  This may take >60s and trigger SIGKILL. Consider using --module or --smoke"
  python tests/test_full_validation.py
fi
