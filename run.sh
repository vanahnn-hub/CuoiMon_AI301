#!/bin/bash
# Script khởi chạy StratAI Agent Localhost
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

export GEMINI_API_KEY="AQ.Ab8RN6KNYAyjFtmst0jZBg4fx32YRNZLnfu3U1VKee32O7GRVw"

echo "=========================================================="
echo "🚀 Đang khởi động StratAI Agent (Đã tích hợp API Key)..."
echo "📍 Địa chỉ máy chủ: http://localhost:8501"
echo "=========================================================="

./venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8501 --reload
