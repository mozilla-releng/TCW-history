====================
Buildbot DB Failover
====================

.. actdiag::
    :desctable:

    #edge_layout = flowchart;

    # prework

    # Communication Points
    # Releng -> MOC
    give_ok_to_start_db_it_work
        -> start_db_it_work ;
    # MOC -> Releng
    give_ok_to_start_releng_bringup
        -> start_selfserve_agents ;

    # main TCW flow
    tcw_start
        -> close_trees
        -> start_non_db_it_work
        -> start_db_it_work
        -> it_done_with_db
        -> give_ok_to_start_releng_bringup
        -> final_check
    -> tcw_end;

    # RelEng shutdown
    close_trees
        -> stop_bb_masters
        -> stop_buildapi
        -> stop_selfserve_agents
        -> verify_no_db_connections
        -> give_ok_to_start_db_it_work ;

    # RelEng bring up
    give_ok_to_start_releng_bringup
        -> start_selfserve_agents
        -> start_buildapi
        -> start_bb_masters
        -> monitor_production 
        -> final_check ;

    # timing dependancies - show as hidden edges to force layout
    #create_scripts -> tcw_start [style=none] ;

    lane MOC {
        label = "MOC" ;
        tcw_start [label="TCW Start",
            numbered=7,
            description="|tcw_start|"] ;
        tcw_end [label="TCW End",
            numbered=21,
            description="|tcw_end|"] ;
        give_ok_to_start_db_it_work ;
        give_ok_to_start_releng_bringup ;
    }

    lane IT {
        label = "IT" ;
        start_non_db_it_work;
        start_db_it_work ;
        it_done_with_db ;
    }

    lane releng {
        label = "RelEng";
        close_trees [label="Close Trees",
            numbered=8,
            description="|close_trees|"] ;

        stop_bb_masters ;
        stop_buildapi ;
        stop_selfserve_agents ;
        verify_no_db_connections ;
        # stop_all_writers [label="Stop BB DB\nwriters",
        #     numbered=9,
        #     description="|stop_all_writers|"] ;

        start_selfserve_agents ;
        start_buildapi ;
        start_bb_masters  ;
        # restart_all_writers [label="Start BB DB\n writers",
        #     numbered=17,
        #     description="|restart_all_writers|"] ;

        monitor_production [label="Monitor RelEng\nSystems",
            numbered=18,
            description="|monitor_production|"] ;
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
.. |log_graphite_data| replace:: Ideally, the delta stats can be
                stored in graphite.
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
