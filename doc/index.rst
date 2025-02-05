.. py:currentmodule:: lsst.ts.mtdomecom

.. _lsst.ts.mtdomecom:

#################
lsst.ts.mtdomecom
#################

TCP/IP interface to the controller for the Simonyi Survey Telescope dome at Vera C. Rubin Observatory.

.. _lsst.ts.mtdomecom-using:

Using lsst.ts.mtdomecom
=======================

.. toctree::
    protocols
    lower_level_commands
    component_statuses
    configuration_parameters
    response_codes
    power_management
    :maxdepth: 2

Build and Test
--------------

This package has the following requirements:

* ts_tcpip
* ts_utils

The package is compatible with LSST DM's ``scons`` build system and ``eups`` package management system.
Assuming you have the basic LSST DM stack installed you can do the following, from within the package directory:

* ``setup -r .`` to setup the package and dependencies.
* ``scons`` to build the package and run unit tests.
* ``scons install declare`` to install the package and declare it to eups.
* ``package-docs build`` to build the documentation.
  This requires ``documenteer``; see `building single package docs`_ for installation instructions.

Usage
-----

The primary classes are:

* `MTDomeCom`: TCP/IP interface to the controller for the Simonyi Survey Telescope dome.
* `MockDomeController`: Simulator for the dome TCP/IP interface.

.. _building single package docs: https://developer.lsst.io/stack/building-single-package-docs.html

.. _lsst.ts.mtdomecom-contributing:

Contributing
============

``lsst.ts.mtdomecom`` is developed at https://github.com/lsst-ts/ts_mtdomecom.
You can find Jira issues for this module using `labels=ts_mtdomcoecom <https://jira.lsstcorp.org/issues/?jql=project%3DDM%20AND%20labels%3Dts_mtdomecom>`_.

.. _lsst.ts.mtdomecom-pyapi:

Python API reference
====================

.. automodapi:: lsst.ts.mtdomecom
    :no-main-docstr:

Version History
===============

.. toctree::
    version_history
    :maxdepth: 1
