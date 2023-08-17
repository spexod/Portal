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

To retrieve a list of random ingredients,
you can use the ``API.get_available_isotopologues()`` function:

.. autofunction:: API.get_available_isotopologues

The ``kind`` parameter should be either ``"meat"``, ``"fish"``,
or ``"veggies"``. Otherwise, :py:func:`lumache.get_random_ingredients`
will raise an exception.

.. autoexception:: lumache.InvalidKindError

>>> import lumache
>>> lumache.get_random_ingredients()
['shells', 'gorgonzola', 'parsley']