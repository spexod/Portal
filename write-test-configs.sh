#!/bin/bash
echo -e "API_BASE_SERVER=http://backend:8000/\nNEXT_PUBLIC_API_BASE_CLIENT=http://localhost/" > ./SpExo-FrontEnd/.env.production
#echo -e "USE_NEW_TABLES = True\nDEBUG = True" > ./SpExWebsite/SpSite/data_config.py
#echo -e "USE_NEW_TABLES = True\nDEBUG = True" > ./SpExWebsite/djangoAPI/data_config.py
#echo -e "do_test_run=true\nreset_status=true\nnew_data_staged=false\nupdated_mysql=false" > ./SpExWebsite/SpExoDisks/ref/data_status.toml
#echo -e "do_test_run=true\nreset_status=false\nnew_data_staged='see server'\nupdated_mysql='see server'" > ./SpExWebsite/SpExoDisks/ref/data_status.toml
