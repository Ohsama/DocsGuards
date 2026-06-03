@echo off
git init
git add .
git commit -m "Initial commit: DocsGuards complete medical scheduling system"
git branch -M main
git remote add origin https://github.com/Ohsama/DocsGuards.git
git push -u origin main
