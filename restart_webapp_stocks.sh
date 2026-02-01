#!/bin/bash

# Stocks Webapp Restart Script
# Purpose: Restart the webapp and run it in the background

set -e

echo "🔄 Stocks Webapp Restart"
echo "======================="
echo ""

# Function to gently stop existing processes
gentle_stop() {
    echo "🛑 Stopping existing webapp processes..."
    
    # Stop Node server
    if [ -f "logs/node-server.pid" ]; then
        local node_pid=$(cat logs/node-server.pid 2>/dev/null || true)
        if [ ! -z "$node_pid" ] && kill -0 "$node_pid" 2>/dev/null; then
            echo "   🟢 Stopping Node.js backend server (PID: $node_pid)"
            kill -TERM "$node_pid" 2>/dev/null || true
            sleep 2
        fi
        rm -f logs/node-server.pid
    fi
    
    # Fallback: Stop any Node servers on port 3001
    local node_pids=$(lsof -ti :3001 2>/dev/null || true)
    if [ ! -z "$node_pids" ]; then
        echo "   🟢 Stopping processes on port 3001: $node_pids"
        echo "$node_pids" | xargs kill -TERM 2>/dev/null || true
        sleep 2
    fi
    
    # Stop using PID file first
    if [ -f "logs/vite.pid" ]; then
        local vite_pid=$(cat logs/vite.pid 2>/dev/null || true)
        if [ ! -z "$vite_pid" ] && kill -0 "$vite_pid" 2>/dev/null; then
            echo "   ⚛️  Stopping Vite dev server (PID: $vite_pid)"
            kill -TERM "$vite_pid" 2>/dev/null || true
            sleep 2
        fi
        rm -f logs/vite.pid
    fi
    
    # Fallback: Stop any Vite processes in this workspace
    local vite_pids=$(ps aux | grep "vite.*stocks/webapp-stocks" | grep -v grep | awk '{print $2}' || true)
    if [ ! -z "$vite_pids" ]; then
        echo "   ⚛️  Stopping remaining Vite processes: $vite_pids"
        echo "$vite_pids" | xargs kill -TERM 2>/dev/null || true
        sleep 2
    fi
    
    echo "   ✅ Gentle stop completed"
}

# Function to start services
start_services() {
    echo "🚀 Starting webapp..."
    
    # Check if we're in the right directory
    if [ ! -d "webapp-stocks" ]; then
        echo "❌ Error: webapp-stocks directory not found"
        exit 1
    fi
    
    # Create logs directory
    mkdir -p logs
    
    echo ""
    echo "🟢 Starting Node.js Backend Server..."
    cd webapp-stocks
    
    # Start Node.js server in background
    nohup node server.js > ../logs/node-server.log 2>&1 &
    NODE_PID=$!
    echo $NODE_PID > ../logs/node-server.pid
    
    # Wait a moment and check if Node started
    sleep 3
    if kill -0 $NODE_PID 2>/dev/null; then
        echo "   ✅ Node.js backend started successfully (PID: $NODE_PID)"
        echo "   📝 Node PID saved to logs/node-server.pid"
    else
        echo "   ❌ Node.js backend failed to start - check logs/node-server.log"
        tail -10 ../logs/node-server.log
        cd ..
        exit 1
    fi
    
    echo ""
    echo "⚛️  Starting Vite Dev Server..."
    
    # Start Vite in background with nohup to detach from terminal
    nohup npm run dev > ../logs/vite.log 2>&1 & 
    VITE_PID=$!
    echo $VITE_PID > ../logs/vite.pid
    
    # Wait a moment and check if Vite started
    sleep 5
    if kill -0 $VITE_PID 2>/dev/null; then
        echo "   ✅ Vite started successfully (PID: $VITE_PID)"
        echo "   📝 Vite PID saved to logs/vite.pid"
    else
        echo "   ❌ Vite failed to start - check logs/vite.log"
        tail -10 ../logs/vite.log
        exit 1
    fi
    
    cd ..
    
    echo ""
    echo "🎉 Webapp is running in background!"
    echo "===================================="
    echo "🟢 Backend:  http://localhost:3001"
    echo "📱 Frontend: http://localhost:5173"
    echo ""
    echo "📝 Logs:"
    echo "   Node:  logs/node-server.log  (tail -f logs/node-server.log)"
    echo "   Vite:  logs/vite.log  (tail -f logs/vite.log)"
    echo ""
    echo "📋 Process IDs:"
    echo "   Node PID:  $(cat logs/node-server.pid 2>/dev/null || echo 'N/A')"
    echo "   Vite PID:  $(cat logs/vite.pid 2>/dev/null || echo 'N/A')"
    echo ""
    echo "🛑 To stop: kill \$(cat logs/node-server.pid) && kill \$(cat logs/vite.pid)"
    echo "🔄 To restart: ./restart_webapp_stocks.sh"
    echo "👁️  Check status: ps aux | grep 'vite.*stocks/webapp-stocks\\|node.*server.js' | grep -v grep"
    echo ""
    echo "💡 Your terminal is now free for other tasks!"
}

# Main execution
echo "🔍 Checking for existing processes..."
gentle_stop
echo ""
start_services

echo "✅ Restart completed successfully!"
