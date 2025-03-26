.. py:currentmodule:: lsst.ts.mtdomecom

.. _lsst.ts.mtdomecom.version_history:

###############
Version History
###############

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
