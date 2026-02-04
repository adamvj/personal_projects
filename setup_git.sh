#!/bin/bash
echo "Initializing Git Repository..."
git init
git remote add origin https://github.com/adamvj/personal_projects.git
git add .
git commit -m "feat: updated nfl cap tracker with real-time data and charts"
git branch -M main
echo "Pushing to GitHub..."
git push -u origin main --force
