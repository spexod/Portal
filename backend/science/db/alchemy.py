from typing import List, Optional

import pandas as pd
import sqlalchemy as sa

from science.db.sql import MYSQL_HOST, sql_port, sql_database, MYSQL_USER,  MYSQL_PASSWORD, MYSQL_CONNECT_OPTIONS
from science.db.sql_values import quote_identifier
# the spectrum formatting lives in its own module (no database) so it can be unit tested; re-exported here
from science.analyze.spectrum_format import (is_good_num, null_val, bandwidth_fraction_for_null_default,
                                              remove_bad_nums, singleton_mask, format_spectrum)


# URL.create escapes the password, an f-string broke on passwords with '@', '/' or '#'
uri_base = sa.engine.URL.create('mysql', username=MYSQL_USER, password=MYSQL_PASSWORD, host=MYSQL_HOST, port=int(sql_port))


class UploadSQL:
    def __init__(self):
        self.engine = sa.create_engine(uri_base, connect_args=MYSQL_CONNECT_OPTIONS)

    def drop_if_exists(self, table_name):
        # engine.execute was removed in SQLAlchemy 2
        with self.engine.begin() as connection:
            connection.execute(sa.text(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}"))

    def upload_table(self, table_name, df, schema=sql_database):
        df.to_sql(table_name, con=self.engine, schema=schema, if_exists='replace', index=False)

    def upload_spectra(self, table_name: str, wavelength_um: List[float], flux: List[float],
                       flux_error: Optional[List[float]] = None, schema: str = sql_database,
                       bandwidth_fraction_for_null: float = bandwidth_fraction_for_null_default):
        structured_array = format_spectrum(wavelength_um=wavelength_um, flux=flux, flux_error=flux_error,
                                           bandwidth_fraction_for_null=bandwidth_fraction_for_null)
        df = pd.DataFrame(structured_array)
        self.upload_table(table_name=table_name, df=df, schema=schema)
