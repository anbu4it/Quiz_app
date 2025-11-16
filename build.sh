#!/usr/bin/env bash
# Render build hook - runs after pip install, before starting the app
# This automatically runs database migrations on every deploy

echo "Running database migrations..."
flask --app wsgi db upgrade

echo "Build hook complete!"
