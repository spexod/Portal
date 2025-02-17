from science.db.data_status import set_data_status_mysql, get_data_status_mysql

# read the status variables from the MySQL server
new_data_staged, new_data_commited, updated_mysql = get_data_status_mysql()
if new_data_staged:
    set_data_status_mysql(new_data_staged_to_set=new_data_staged, new_data_commited_to_set=True, updated_mysql_to_set=False)