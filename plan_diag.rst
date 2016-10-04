===================
InnoDB Cutover Plan
===================

Legend:

    - blue links are TCW work not related to InnoDB cutover
    - red links are "sad path" - we hope not to use them
    - green links are "happy path" - we want to be there.

.. actdiag::
    :desctable:

    #edge_layout = flowchart;

    # prework
    start -> create_scripts ; # stretch
    start -> check_replication_status -> cutover_ro_instance ;
    create_scripts -> log_graphite_data; # stretch
    cutover_ro_instance -> monitor ;

    tcw_start -> close_trees -> stop_all_writers ;
    tcw_start -> tcw_pre_db [style=dashed, color=blue] ;
    stop_all_writers -> verify_replication ;
    tcw_pre_db -> apply_all_patches_and_reboot -> failover_to_innodb ;
    verify_replication -> failover_to_innodb ;
    failover_to_innodb -> monitor_rw_db ;
    monitor_rw_db -> okay_on_innodb ;
    okay_on_innodb -> rollback_to_myisam_for_rw [label="No", color=red, textcolor=red]; # original master
    rollback_to_myisam_for_rw -> restart_all_writers ;
    okay_on_innodb -> restart_all_writers [label="Yes", color=green, textcolor=green];
    restart_all_writers -> monitor_production ;
    monitor_production -> declare_victory ;
    declare_victory -> tcw_post_db ;
    tcw_post_db -> tcw_end [style=dashed, color=blue];

    # timing dependancies - show as hidden edges to force layout
    log_graphite_data -> tcw_start [style=none] ;
    monitor -> tcw_start [style=none] ;
    stop_all_writers -> tcw_pre_db [style=none] ;
    tcw_pre_db -> verify_replication [style=none] ;

    lane MOC {
        label = "MOC" ;
        tcw_start [label="TCW Start",
            numbered=7,
            description="|tcw_start|"] ;
        tcw_pre_db [label="TCW before\nDB work",
            numbered=10,
            description="|tcw_pre_db|"] ;
        tcw_post_db [label="TCW after\nDB work",
            numbered=20,
            description="|tcw_post_db|"] ;
        tcw_end [label="TCW End",
            numbered=21,
            description="|tcw_end|"] ;
    }

    lane data {
        label = "Data Team" ;
        cutover_ro_instance [label="Switch R/O VIP\nto InnoDB",
            numbered=4,
            description="|cutover_ro_instance|"] ;
        apply_all_patches_and_reboot [label="Update Nodes",
            numbered=12,
            description="|apply_all_patches_and_reboot|"] ;
        failover_to_innodb [label="Switch R/W VIP\nto InnoDB",
            numbered=13,
            description="|failover_to_innodb|"] ;
        monitor_rw_db [label="Monitor R/W Node",
            numbered=14,
            description="|monitor_rw_db|"] ;
        rollback_to_myisam_for_rw [label="Rollback to MyISAM",
            numbered=16,
            description="|rollback_to_myisam_for_rw|"] ; # original master
    }

    lane releng {
        label = "RelEng";
        start [label="Start\nWork",
            numbered=1,
            description="|start|"] ; # stretch
        check_replication_status [label="Are replicas\ncurrent enough?",
            numbered=2,
            description="|check_replication_status|"] ;
        create_scripts [label="Write Scripts",
            numbered=3,
            description="|create_scripts|"] ;
        log_graphite_data [label="Graph Deltas",
            numbered=5,
            description="|log_graphite_data;|"] ; # stretch
        monitor [label="Look for R/O issues",
            numbered=6,
            description="|monitor|"] ;

        close_trees [label="Close Trees",
            numbered=8,
            description="|close_trees|"] ;
        stop_all_writers [label="Stop BB DB\nwriters",
            numbered=9,
            description="|stop_all_writers|"] ;
        verify_replication [label="Verify Replication\ncaught up",
            numbered=11,
            description="|verify_replication|"] ;
        okay_on_innodb [label="Is\nInnoDB\nGood?",
            numbered=15,
            description="|okay_on_innodb|", shape=diamond];
        restart_all_writers [label="Start BB DB\n writers",
            numbered=17,
            description="|restart_all_writers|"] ;
        monitor_production [label="Monitor RelEng\nSystems",
            numbered=18,
            description="|monitor_production|"] ;
        declare_victory [label="Final 'Go for\nProduction'",
            numbered=19,
            description="|declare_victory|"] ;
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
.. |failover_to_innodb| replace:: Point the r/w VIP at the InnoDB r/w
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
.. |create_scripts| replace:: Write scripts needed to monitor
                replication deltas.
.. |log_graphite_data;| replace:: Ideally, the delta stats can be
                stored in graphite.
.. |monitor| replace:: Look at all RelEng systems for any problems or
                anomalies.
.. |close_trees| replace:: Normal tree closure procedure for TCW.
.. |stop_all_writers| replace:: Stop all writers to the buildbot
                databases. This includes (at least) the buildbot
                masters, scheduler masters, and buildbot bridge.
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
                the buildbot databases.
.. |monitor_production| replace:: Continue initial monitoring that
                things "look okay". 
.. |declare_victory| replace:: Formal acceptance of InnoDB in
                production. (Corollary is last chance to ask for
                rollback. That path not shown, but "obvious".)
