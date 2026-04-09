#!/bin/bash

# Function to handle cleanup on script exit
cleanup() {
    echo "Stopping all processes..."
    kill 0
}

# Set up to catch termination signals (like Ctrl+C) and run cleanup
trap cleanup SIGINT SIGTERM EXIT

echo "========================================="
echo "Starting AMD Hackathon Project"
echo "========================================="

echo "[1/2] Starting Python backend..."
python app.py &

echo "[2/2] Starting Vite React frontend..."
cd frontend || exit
npm run dev &

echo "========================================="
echo "Both frontend and backend are running!"
echo "Press Ctrl+C to stop both servers."
echo "========================================="

# Keep the script running to wait for the background processes
wait
