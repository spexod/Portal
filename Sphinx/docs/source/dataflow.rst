DataFlow
========

Before we begin with our API package, it's important to understand the data flow of the application.

The database is seperated by the following labels:

.. csv-table:: Spectra
   :file: csvs/Spectra.csv
   :widths: 30, 70
   :header-rows: 1

.. csv-table:: Curated
   :file: csvs/curated.csv
   :widths: 30, 70
   :header-rows: 1

.. csv-table:: Objectnamealiases
   :file: csvs/objectnamealiases.csv
   :widths: 30, 70
   :header-rows: 1

.. csv-table:: Available_isotopologues
   :file: csvs/availableiso.csv
   :widths: 30, 70
   :header-rows: 1

.. csv-table:: Available_params_and_units
   :file: csvs/params_units.csv
   :widths: 30, 70
   :header-rows: 1

.. csv-table:: Isotopologue_*****
   :file: csvs/isotopologues.csv
   :widths: 30, 70
   :header-rows: 1

.. csv-table:: Spectrum_handle
   :file: csvs/spectrum_handle.csv
   :widths: 30, 70
   :header-rows: 1

The following diagram shows the data flow of the application to have a better understanding of the
database structure and how to properly look up the data.

.. figure:: SpExoDisks.png
    :align: center
    :width: 80%