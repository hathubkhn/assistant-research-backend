#!/bin/bash

# Ensure we're using PostgreSQL by setting environment variable
export USE_POSTGRES=True

# Run the sync_users command
echo "Syncing users between research_asssistant_db and auth_db..."
python manage.py sync_users "$@"

echo "User synchronization completed." 