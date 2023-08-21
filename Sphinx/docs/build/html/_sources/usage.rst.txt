Usage
=====

.. _installation:

Installation
------------

To use SpExod, first install it using pip:

.. code-block:: console

   (.venv) $ pip install spexod

Or try one of the other installation methods.

.. code-block:: console

   (.venv) $ conda install -c conda-forge spexod

Or

.. code-block:: console

    git clone https://github.com/spexod/spexod cd spexod pip install .


Retrieving Data
-------------------
.. note::

   It may be helpful to view the :doc:`dataflow` source page as you follow along with the documentation.

The following functions are used to retrieve almost all data from the database:
``API.get_available_isotopologues()``, ``get_params_and_units()``, ``get_curated()``, ``get_spectra()``,
and ``get_star_aliases()``. Each of these functions returns a list of dictionaries, where each dictionary
represents a row in the database. The keys of the dictionaries are the column names of the database,

.. autofunction:: API.get_available_isotopologues

.. autofunction:: API.get_params_and_units

.. autofunction:: API.get_curated

.. autofunction:: API.get_spectra

.. autofunction:: API.get_star_aliases

Navigating the SpExoDisks Database
----------------------------------

.. warning::

    If the alias is not typed verbatim as it is in the database, it will return a list of similar
    aliases. Just copy and paste the alias you want to search for into the find_spectra_handle() function and it will
    return a list of dictionaries of the spectra associated with the alias.

.. autofunction:: API.find_spectra_handle
.. autofunction:: API.get_curated_data
.. autofunction:: API.get_all_spectra_handles
.. autofunction:: API.get_wavelengths
.. autofunction:: API.get_fluxes

Misc Functions
--------------
.. autofunction:: API.get_stars_from_file
.. autofunction:: API.create_spectra_file
.. autofunction:: API.download_spectrum
.. autofunction:: API.plot_spectra

.. note::

    To see a working example of the API, check out the :doc:`examples` section. And also
    the following jupyter notebook: https://github.com/spexod/spexod/blob/python_api_tool/getting_started.ipynb