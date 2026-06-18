#!/bin/bash
sudo docker-compose -f /opt/intent-test-framework/docker-compose.prod.yml exec -T new-agents-backend python -c "from app import app, init_db; init_db(app)"
