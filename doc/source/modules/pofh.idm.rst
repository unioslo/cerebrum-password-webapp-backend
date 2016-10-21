========
pofh.idm
========
The IdM client performs the actual password change, and fetches information on
users and persons.

.. automodule:: pofh.idm
   :members:

mock client
===========
.. automodule:: pofh.idm.client
   :members:

mock data
---------
The mock client can be populated by setting the ``IDM_MOCK_DATA`` setting to a
JSON or YAML file with data.

JSON-files must end in ``.json``, and YAML-files must end in ``.yml`` or
``.yaml``. If the setting is not set to an absolute path, the file name will be
assumed to be relative to the application instance path.

``mock_data.json``
    .. literalinclude:: example.idm_mock_data.json
       :language: json


``mock_data.yml``
    .. literalinclude:: example.idm_mock_data.yml
       :language: yaml


cerebrum-api client
===================
.. automodule:: pofh.idm.cerebrum_api_v1
   :members:
