#!/bin/bash
# 舆情系统一键启动脚本
# 用法: ./start-services.sh [start|stop|restart|status]

set -e

PROJECT_DIR="/root/.openclaw/workspace/sentiment-analysis"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV="$BACKEND_DIR/venv/bin/activate"
LOG="/tmp/sentiment-services.log"

start_backend() {
    if pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
        echo "后端服务已在运行 (PID: $(pgrep -f 'uvicorn app.main:app' | head -1))"
        return 0
    fi
    cd "$BACKEND_DIR"
    . "$VENV"
    PYTHONPATH="$PROJECT_DIR:$BACKEND_DIR" nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
    echo "后端服务已启动 (PID: $!)"
}

stop_backend() {
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    echo "后端服务已停止"
}

start_nginx() {
    if [ -f /run/nginx.pid ] && kill -0 $(cat /run/nginx.pid) 2>/dev/null; then
        echo "nginx 已在运行 (PID: $(cat /run/nginx.pid))"
        /usr/sbin/nginx -s reload 2>/dev/null || true
    else
        /usr/sbin/nginx
        echo "nginx 已启动"
    fi
}

stop_nginx() {
    /usr/sbin/nginx -s stop 2>/dev/null || true
    echo "nginx 已停止"
}

status() {
    echo "=== 服务状态 ==="
    if pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
        PID=$(pgrep -f 'uvicorn app.main:app' | head -1)
        echo "后端: 运行中 (PID: $PID)"
        curl -s -o /dev/null -w "后端健康检查: HTTP %{http_code}\n" http://localhost:8000/docs
    else
        echo "后端: 未运行"
    fi
    
    if [ -f /run/nginx.pid ] && kill -0 $(cat /run/nginx.pid) 2>/dev/null; then
        echo "nginx: 运行中 (PID: $(cat /run/nginx.pid))"
        curl -s -o /dev/null -w "前端健康检查: HTTP %{http_code}\n" http://localhost/
    else
        echo "nginx: 未运行"
    fi
}

case "${1:-start}" in
    start)
        start_backend
        start_nginx
        status
        ;;
    stop)
        stop_backend
        stop_nginx
        ;;
    restart)
        stop_backend
        stop_nginx
        sleep 1
        start_backend
        start_nginx
        status
        ;;
    status)
        status
        ;;
    *)
        echo "用法: $0 [start|stop|restart|status]"
        exit 1
        ;;
esac
