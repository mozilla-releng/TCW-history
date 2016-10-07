..
    Color code for chart:
        - white -- not started yet
        - lightgreen -- done
        - orchid -- in progress
        - maroon -- cancelled

===================
InnoDB Cutover Plan
===================

Legend:

    - blue links are TCW work not related to InnoDB cutover
    - red links are "sad path" - we hope not to use them at a decision
      point
    - green links are "happy path" - we want to be there after a
      decision point

.. actdiag::
    :desctable:

    #edge_layout = flowchart ;

    # prework
    start -> create_DB_scripts -> log_graphite_data ;
    start -> create_ops_scripts ;  # stretch
    start -> check_replication_status -> cutover_ro_instance ;
    cutover_ro_instance -> monitor -> disable_db_maintenance ->
        close_trees ;
    disable_db_maintenance ; 

    close_trees ;
    tcw_start -> verify_trees_closed -> stop_all_writers ;
    tcw_start -> tcw_pre_db [style=dashed, color=blue] ;
    stop_all_writers -> verify_empty_command_queues -> verify_replication ;
    tcw_pre_db -> apply_all_patches_and_reboot -> failover_to_innodb ;
    verify_replication -> failover_to_innodb ;
    failover_to_innodb -> monitor_rw_db ;
    monitor_rw_db -> okay_on_innodb ;
    okay_on_innodb -> rollback_to_myisam_for_rw [label="No", color=red, textcolor=red] ; # original master
    rollback_to_myisam_for_rw -> restart_all_writers ;
    okay_on_innodb -> restart_all_writers [label="Yes", color=green, textcolor=green] ;
    restart_all_writers -> monitor_production ;
    monitor_production -> declare_victory ;
    declare_victory -> tcw_post_db ;
    tcw_post_db -> tcw_end [style=dashed, color=blue] ;
    manually_run_db_maintenance -> reenable_db_maintenance ; 

    # timing dependancies - show as hidden edges to force layout
    create_ops_scripts -> tcw_start [style=none]
    close_trees -> tcw_start [style=none]
    disable_db_maintenance -> tcw_start [style=none] ;
    log_graphite_data -> tcw_start [style=none] ;
    monitor -> tcw_start [style=none] ;
    stop_all_writers -> tcw_pre_db [style=none] ;
    tcw_pre_db -> verify_replication [style=none] ;
    tcw_end -> manually_run_db_maintenance [style=none] ;

    lane MOC {
        label = "MOC" ;
        tcw_start [label="TCW Start",
            color=white,
            numbered=70,
            description="|tcw_start|"] ;
        tcw_pre_db [label="TCW before\nDB work",
            color=white,
            numbered=100,
            description="|tcw_pre_db|"] ;
        tcw_post_db [label="TCW after\nDB work",
            color=white,
            numbered=200,
            description="|tcw_post_db|"] ;
        tcw_end [label="TCW End",
            color=white,
            numbered=210,
            description="|tcw_end|"] ;
    }

    lane data {
        label = "Data Team" ;
        cutover_ro_instance [label="Switch R/O VIP\nto InnoDB",
            color=lightgreen,
            numbered=40,
            description="|cutover_ro_instance|"] ;
        apply_all_patches_and_reboot [label="Update Nodes",
            color=white,
            numbered=120,
            description="|apply_all_patches_and_reboot|"] ;
        failover_to_innodb [label="Switch R/W VIP\nto InnoDB",
            color=white,
            numbered=130,
            description="|failover_to_innodb|"] ;
        monitor_rw_db [label="Monitor R/W Node",
            color=white,
            numbered=140,
            description="|monitor_rw_db|"] ;
        rollback_to_myisam_for_rw [label="Rollback to MyISAM",
            color=white,
            numbered=160,
            description="|rollback_to_myisam_for_rw|"] ; # original master
    }

    lane releng {
        label = "RelEng" ;
        start [label="Start\nWork",
            color=lightgreen,
            numbered=10,
            description="|start|"] ; # stretch
        check_replication_status [label="Are replicas\ncurrent enough?",
            color=lightgreen,
            numbered=20,
            description="|check_replication_status|"] ;
        create_DB_scripts [label="Write DB Scripts",
            color=lightgreen,
            numbered=30,
            description="|create_DB_scripts|"] ;
        create_ops_scripts [label="Write TCW Scripts",
            color=white,
            numbered=32,
            description="|create_ops_scripts|"] ;
        log_graphite_data [label="Graph Deltas",
            color=white,
            numbered=50,
            color=lightgreen,
            description="|log_graphite_data|"] ; # stretch
        monitor [label="Look for R/O issues",
            color=white,
            numbered=60,
            description="|monitor|"] ;
        disable_db_maintenance [label="Disable DB Maint",
            color=white,
            numbered=65,
            description="|disable_db_maintenance|"] ;

        close_trees [label="Close Trees",
            color=white,
            numbered=80,
            description="|close_trees|"] ;
        verify_trees_closed [label="Check Tree Status",
            color=white,
            numbered=85,
            description="|verify_trees_closed|"] ;
        stop_all_writers [label="Stop BB DB\nwriters",
            color=white,
            numbered=90,
            description="|stop_all_writers|"] ;
        verify_empty_command_queues [label="Empty Queues",
            color=white,
            numbered=91,
            description="|verify_empty_command_queues|"] ;
        verify_replication [label="Verify Replication\ncaught up",
            color=white,
            numbered=110,
            description="|verify_replication|"] ;
        okay_on_innodb [label="Is\nInnoDB\nGood?",
            color=white,
            numbered=150,
            description="|okay_on_innodb|", shape=diamond] ;
        restart_all_writers [label="Start BB DB\n writers",
            color=white,
            numbered=170,
            description="|restart_all_writers|"] ;
        monitor_production [label="Monitor RelEng\nSystems",
            color=white,
            numbered=180,
            description="|monitor_production|"] ;
        declare_victory [label="Final 'Go for\nProduction'",
            color=white,
            numbered=190,
            description="|declare_victory|"] ;
        manually_run_db_maintenance [label="Run DB Maintenance",
            color=white,
            numbered=220,
            description="|manually_run_db_maintenance|"];
        reenable_db_maintenance [label="Renable DB Maint",
            color=white,
            numbered=230,
            description="|reenable_db_maintenance|"] ;
    }


.. |tcw_start| replace:: Start of TCW
.. |tcw_pre_db| replace:: All work scheduled before start of Buildbot
                Database work.
.. |tcw_post_db| replace:: All work scheduled after Buildbot Database
                work.
.. |tcw_end| replace:: End of TCW
.. |apply_all_patches_and_reboot| replace:: Apply all needed firmware
                and software updates. Since this includes a kernel
                update in many cases, a reboot is required.
.. |failover_to_innodb| replace:: Two steps: 1) remove MyISAM db's from
                being replication targets (effectively a backup in case
                of rollback). 2) Point the r/w VIP at the InnoDB r/w
                node.
.. |cutover_ro_instance| replace:: Point the r/o VIP at the InnoDB r/o
                node.
.. |rollback_to_myisam_for_rw| replace:: **FAILED InnoDB** so rollback
                to the original MyISAM instances for production.
.. |start| replace:: Start working on all the plans, scripts, etc.
                needed for the TCW work.
.. |check_replication_status| replace:: Verify via the releng methods
                that the master and replica appear "close enough" to cut
                over.
.. |create_DB_scripts| replace:: Write scripts needed to monitor
                replication deltas.
.. |create_ops_scripts| replace:: Create or document where scripts are
                that can help during TCW. E.g. ansible scripts, etc.
.. |log_graphite_data| replace:: Ideally, the delta stats can be
                stored in graphite.
.. |monitor| replace:: Look at all RelEng systems for any problems or
                anomalies.
.. |disable_db_maintenance| replace:: Usually runs Sunday midnight PT.
                Disable for this weekend (will be run manually later).
.. |close_trees| replace:: Normal tree closure procedure for TCW, plus a
                graceful shutdown of buildbot database writers. This may
                be earlier than start of TCW.
.. |verify_trees_closed| replace:: They may have been closed earlier,
                but need to confirm at this point.
.. |stop_all_writers| replace:: Stop all writers to the buildbot
                databases. This includes (at least) the buildbot
                masters, scheduler masters, and `buildbot bridge`_.
                Ideally, this is done as a "graceful" stop early, with a
                hard stop when needed (per Nick). Also shutdown
                selfserve via supervisord.
.. |verify_empty_command_queues| replace:: After shutting down all
                masters we should make sure the command queue has
                emptied (per Nick).
.. |verify_replication| replace:: Final readiness check by RelEng that
                r/w masters are identical between MyISAM & InnoDB
                versions. Note that this is a while after all writing
                has been stopped, so all replication lag should have
                dissipated.
.. |monitor_rw_db| replace:: After cutover, look for any
                issues reported on the DB side.
.. |okay_on_innodb| replace:: RelEng makes the call as to whether the
                InnoDB configuration is good enough for production use.
.. |restart_all_writers| replace:: Restart all services which write to
                the buildbot databases. This is done in 3 steps:
                a) trial load (try builds & tests on existing builds);
                b) full load; and c) restart workers to force reconnect
                if required. [#workers]
.. |monitor_production| replace:: Continue initial monitoring that
                things "look okay". 
.. |declare_victory| replace:: Formal acceptance of InnoDB in
                production. (Corollary is last chance to ask for
                rollback. That path not shown, but "obvious".)
.. |manually_run_db_maintenance| replace:: If we've successfully
                switched to InnoDB, the weekly maintence should be run
                under supervision, in case changes are needed. Time TBD.
.. |reenable_db_maintenance| replace:: Re-enable the cronjob for the
                weekly maintenance.

.. rubric:: Footnotes

.. [#workers] From Nick's email:
        The buildbot slaves/workers have a backoff in their reconnection
        loop, so after a few hours of masters stopped they may be
        waiting a long time between attempts. We may need to reboot
        hardware slaves to get them to connect again. AWS instances are
        likely to have been reaped by then, and there's a known slow
        response from watch_pending if a lot of build load arrives.


.. _buildbot bridge: https://wiki.mozilla.org/ReleaseEngineering/Applications/BuildbotBridge#How_to_restart_the_services
