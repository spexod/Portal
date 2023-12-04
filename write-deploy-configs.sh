#!/bin/bash
echo -e "API_BASE_SERVER=http://backend:8000/\nNEXT_PUBLIC_API_BASE_CLIENT=https://spexodisks.com/" > ./SpExo-FrontEnd/context/.env.production
echo -e "USE_NEW_TABLES = False\nDEBUG = False" > ./SpExWebsite/SpSite/data_config.py
echo -e "USE_NEW_TABLES = False\nDEBUG = False" > ./SpExWebsite/djangoAPI/data_config.py
echo -e "do_test_run=false\nreset_status=false\nnew_data_staged='see server'\nupdated_mysql='see server'" > ./SpExWebsite/SpExoDisks/ref/data_status.toml
