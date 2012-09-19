elvard-fabfile
==============

My fabfile used to manage Django powered sites, using Git and Virtualenv.

Basics
------

My goal is use Git for versioning and deploying, Virtualenv for creating
known environments and Fabric for automated workflow.

The ideal workflow should look like this:

* Local development and testing using temporary database and local settings
* Deployment to **staging** enviroment, which has the same properties as
  production one. The only difference is DEBUG = True.
* Run tests on **staging** version.
* If tests runs well, deploy to **production** environment and tag this version
  in `git`.

Stages
------

Three stages, **development**, **staging** and **production** have three
related branches in Git: **dev**, **staging** and **stable**.

.. note:: *Stable* branch should be probably renamed to *production*.

Development
^^^^^^^^^^^

Local settings: testing database (SQLite, unless I need run database-specific
code), cache disabled, SECRET_KEY = 42, etc.

Staging
^^^^^^^

Production settings with DEBUG = True. This runs on server in virtual
environment similar to production one. Accessed on <host>:8080 with HTTP
Authentication.

Production
^^^^^^^^^^

Final version, production settings, visible for all users.

Settings
--------

Settings are divided into 4 files under ``<project_dir>/settings``:

* defaults.py -- with all common settings, almost everything from original
  settings.py
* development.py -- inherit from defaults.py, DEBUG = True, disabled cached, etc.
* staging.py -- inherit from defaults.py and production.py, just set DEBUG = True
* production.py -- inherit from defaults.py, production settings. This is the
  only file which contains sensitive data as passwords, secret key, etc. All
  others could be used for debugging purposes.


Example usage
-------------

Create ``fabfile.py`` in your project directory and add your own environment
settings.

.. code:: python

    from elvard.fabfile import *

    env.hosts = ['tomas-ehrlich_cz@tomas-ehrlich.cz:22122']
    env.project_dir = 'src'
    env.activate = 'env/bin/activate'
    env.wsgi = 'tomas_ehrlich.wsgi.py'
    env.repository = 'tomas_ehrlich.git'
    stages = {'staging': {'master': 'staging',
                 'slave': 'dev',
                 'directory': '~/dev',
                 'settings': 'staging'},
     'stable': {'master': 'stable',
                'slave': 'staging',
                'directory': '~/web',
                'settings': 'production'}}
