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


Creating recipes
----------------

To retrieve a list of random ingredients,
you can use the ``lumache.get_random_ingredients()`` function:

.. autofunction:: lumache.get_random_ingredients

   Return a list of random ingredients as strings.

   :param kind: Optional "kind" of ingredients.
   :type kind: list[str] or None
   :return: The ingredients list.
   :rtype: list[str]

The ``kind`` parameter should be either ``"meat"``, ``"fish"``,
or ``"veggies"``. Otherwise, :py:func:`lumache.get_random_ingredients`
will raise an exception.

.. autoexception:: lumache.InvalidKindError

>>> import lumache
>>> lumache.get_random_ingredients()
['shells', 'gorgonzola', 'parsley']