#!/bin/bash
sudo docker-compose -f /opt/intent-test-framework/docker-compose.prod.yml exec -T new-agents-backend python -c "from app import app, init_db; import sys; sys.path.append('/app'); app.app_context().push(); init_db()"
