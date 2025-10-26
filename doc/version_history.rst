.. py:currentmodule:: lsst.ts.mtdomecom

.. _lsst.ts.mtdomecom.version_history:

###############
Version History
###############

.. towncrier release notes start

v0.3.4 (2025-10-26)
===================

New Features
------------

- Added louvers details doc. (`OSW-1057 <https://rubinobs.atlassian.net//browse/OSW-1057>`_)
- Added AMCS and ThCS telemetry details doc. (`OSW-1057 <https://rubinobs.atlassian.net//browse/OSW-1057>`_)


Bug Fixes
---------

- Fix python package name. (`OSW-1057 <https://rubinobs.atlassian.net//browse/OSW-1057>`_)
- Fix ThCS schema file name. (`OSW-1057 <https://rubinobs.atlassian.net//browse/OSW-1057>`_)


Performance Enhancement
-----------------------

- Loading enabled louvers from a config file. (`OSW-1057 <https://rubinobs.atlassian.net//browse/OSW-1057>`_)


v0.3.3 (2025-10-23)
===================

Other Changes and Additions
---------------------------

- Formatted code with ruff. (`OSW-1058 <https://rubinobs.atlassian.net//browse/OSW-1058>`_)


v0.3.2 (2025-10-09)
===================

Performance Enhancement
-----------------------

- Updated ts-conda-build dependency version and conda build string. (`OSW-1207 <https://rubinobs.atlassian.net//browse/OSW-1207>`_)


v0.3.1 (2025-09-22)
===================

Bug Fixes
---------

- Fixed aperture shutter home command direction parameter. (`OSW-1066 <https://rubinobs.atlassian.net//browse/OSW-1066>`_)


v0.3.0 (2025-09-14)
===================

New Features
------------

- Added option to enable new temperature telemetry schema. (`OSW-331 <https://rubinobs.atlassian.net//browse/OSW-331>`_)
- Added resetDrivesLouvers command. (`OSW-1042 <https://rubinobs.atlassian.net//browse/OSW-1042>`_)
- Added log message indicating which louvers are enabled. (`OSW-1042 <https://rubinobs.atlassian.net//browse/OSW-1042>`_)
- Enabled all LCS commands. (`OSW-1042 <https://rubinobs.atlassian.net//browse/OSW-1042>`_)


Bug Fixes
---------

- Added missing 'direction' parameter to home command. (`OSW-1042 <https://rubinobs.atlassian.net//browse/OSW-1042>`_)
- Added reporting exception in status when not connected. (`OSW-1060 <https://rubinobs.atlassian.net//browse/OSW-1060>`_)


Performance Enhancement
-----------------------

- Removed all references to the old ApSCS states. (`OSW-1042 <https://rubinobs.atlassian.net//browse/OSW-1042>`_)
- Removed all references to the old thermal schema. (`OSW-1042 <https://rubinobs.atlassian.net//browse/OSW-1042>`_)


v0.2.15 (2025-08-08)
====================

Performance Enhancement
-----------------------

- Handle CancelledError better. (`OSW-806 <https://rubinobs.atlassian.net//browse/OSW-806>`_)


v0.2.14 (2025-08-01)
====================

Performance Enhancement
-----------------------

- Handle timeout errors with the fixed cRIO better. (`OSW-716 <https://rubinobs.atlassian.net//browse/OSW-716>`_)
- Stop running tasks with a condition instead of canceling them. (`OSW-716 <https://rubinobs.atlassian.net//browse/OSW-716>`_)
- Reduced the number of error and warning messages for commands that have not received a reply. (`OSW-716 <https://rubinobs.atlassian.net//browse/OSW-716>`_)


v0.2.13 (2025-06-11)
====================

New Features
------------

- Switch to towncrier. (`OSW-328 <https://rubinobs.atlassian.net//browse/OSW-328>`_)


Bug Fixes
---------

- Fix version module import. (`OSW-328 <https://rubinobs.atlassian.net//browse/OSW-328>`_)


Performance Enhancement
-----------------------

- Improve error reporting in case of a WiFi communication error. (`OSW-328 <https://rubinobs.atlassian.net//browse/OSW-328>`_)


=======
v0.2.12
=======

* Avoid unnecessary 'Not handling invalid target state' messages.
* Ensure that the ApSCS simulator correctly opens and closes.

=======
v0.2.11
=======

* Add GitHub actions.
* Improve handling of communication errors between the fixed and rotating parts.

=======
v0.2.10
=======

* Add temporary mapping for ApSCS states until XML 23.2 is released.
* Rename the searchZeroShutter command to home.
  For now it only supports homing the shutter.
  This needs to be revised if additional home commands are introduced in the future.

======
v0.2.9
======

* Remove ts_idl dependency from conda recipe and add ts_xml.

======
v0.2.8
======

* Add support for the capacitor banks dcBusVoltage telemetry item.

======
v0.2.7
======

* Enable the ApSCS setOperationalMode command.

======
v0.2.6
======

* Rewrite status commands task.

======
v0.2.5
======

* The status command does not wrap with the asyncio task by default.

======
v0.2.4
======

* Add the argument in ``MTDomeCom.one_periodic_task()`` to decide to wrap the callback or not to improve the performance.

======
v0.2.3
======
* Exit fault of APSCS under the normal operation.
* Add the lock to execute the non-status command first compared with the status related commands.
* Unify the tasks of state queries to a single one.

Requires:

* ts_tcpip
* ts_utils

======
v0.2.2
======
* Fix a tiny bug in the AMCS simulator.

Requires:

* ts_tcpip
* ts_utils

======
v0.2.1
======
* Make sure that the MotionState enum always is used as a string instead of an int.
* Make sure that the capacitor banks telemetry has the correct data types.
* Spelling and punctuation corrections.
* Split up exitFault to one command per subsystem.
* Add infrastructure to request subsystem statuses regularly.
* Fix race condition in telemetry code.

Requires:

* ts_tcpip
* ts_utils

======
v0.2.0
======
* Enable uploading documentation.
* Import all schemas.
* Extract all constants to a constants file.

Requires:

* ts_tcpip
* ts_utils

======
v0.1.0
======

* First release of the MTDome TCP/IP interface.
  All non-CSC code and documentation were moved from ts_mtdome to this project.

Requires:

* ts_tcpip
* ts_utils
