#!/bin/bash
echo -e "export const useServer=true;" > ./SpExo-FrontEnd/front-app/src/api_config.js
echo -e "USE_NEW_TABLES = False\nDEBUG = False" > ./SpExWebsite/SpSite/data_config.py
echo -e "do_test_run=false\nreset_status=false\nnew_data_staged='see server'\nupdated_mysql='see server'" > ./SpExWebsite/SpExoDisks/ref/data_status.toml
