:orphan:

====================================
MyISAM -> InnoDB Prep & Cutover Plan
====================================

A quick and dirty set of scripts and plans for the TCW.

What's here:
============

Code
----
monitor_replication.py
   Script to do too much: collect row counts, compare counts between
   replicas, and post differences to graphite

monitor_replication.ini
   Configuration of which databases on each host to query, and which
   tables in each database to query.

Docs
----
plan_diag.rst |rtfd|
   The meat of the plan, uses actdiag extension to Sphinx

.. |rtfd| image:: https://readthedocs.org/projects/innodb-cutover/badge/
    :target: http://innodb-cutover.readthedocs.io/
    :alt: Documentation Status

Makefile conf.py index.rst make.bat
   Sphinx boiler plate

What's not here:
================

Credentials
   to access datbases, you need to provide a MySQL ini file specifying
   host, port, user, password. These should have an extension of
   "``.ini``" (which is .gitignored to avoid an oops). The name should
   be useful in identifying the host, as it will be used in the graphite
   path of the collected data.
