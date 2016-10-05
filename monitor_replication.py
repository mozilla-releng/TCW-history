#!/usr/bin/env python
"""
%prog [options] <master_cred_or_data_file> [<replica_cred_or_data_file>...]
Report "replication discrepancies" and optionally log to graphite.

where *file arguements are either:
    - MySQL options files with credentials for the respective server
      (--nocompare option)
    - Previously captured data files (--process option)

Two use cases are envisioned:
    - build a graph-over-time of replication discrepancies
    - provide a snapshot of status (e.g. before a cutover)

For this purpose, lag is defined as the difference in row counts between
the r/w & r/o nodes. This value is expected to be non-zero at times, but
on average be very low. A more timeconsuming and accurate check of
replication consistancy is run twice a day by the data team, and alerted
if there are any inconsistancies.

Intended to be run on host with:
    - Access to both r/o and r/w connections to the buildbot databases.
    - Also needs a flow to the graphite server.
    - Works with python 2.6.6 (version on database servers)
"""
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import re
import socket
from subprocess import Popen, PIPE
log = logging.getLogger(__name__)

__version__ = '0.1'
TABLE_SECTION_TEMPLATE = "Tables_in_%s"
CREDENTIAL_SECTION_TEMPLATE = "db_credentials_for_%s"
GRAPHITE_TEMPLATE = "test.hwine.test.bbdb.%s.%s %d %d"
GRAPHITE_SERVER = "graphite-relay.private.scl3.mozilla.com"
GRAPHITE_PORT = 2003

# dreaded globals
sock = None

def parse_args():
    from optparse import OptionParser
    parser = OptionParser(usage=__doc__, version=__version__)
    parser.set_defaults(
        loglevel=logging.INFO,
        logfile=None,
        config_file="monitor_replication.ini",
        compare=True,
        process_only=False,
        record_data=False,
    )
    parser.add_option("-l", "--logfile", dest="logfile")
    parser.add_option("--config", dest="config_file",
            help="config file for tables to be searched")
    parser.add_option("-v", "--verbose", dest="loglevel", action="store_const",
                      const=logging.DEBUG, help="run verbosely")
    parser.add_option("-q", "--quiet", dest="loglevel", action="store_const",
                      const=logging.WARNING, help="run quietly")
    parser.add_option("--record-data", action="store_true", help="post to graphite")
    parser.add_option("--nocompare", dest="compare",
                      action="store_false", help="only collect data")
    parser.add_option("--process", dest="process_only", action="store_true",
                      help="process existing data files")
    options, args = parser.parse_args()

    if not len(args):
        parser.error("Missing credential files")
    elif options.record_data and not options.compare:
        parser.error("you can't record data without a comparison")
    return options, args

class StepHeader(object):
    def __init__(self):
        self.next_step = 0
    def next(self, text=None):
        self.next_step += 1
        commands = []
        if text:
            commands.append('''select "Step %s - '%s':" as "" ;''' %
                    (self.next_step, text))
            commands.append(text)
        else:
            commands.append('select "Step %s:" as "" ;' % self.next_step)
        return commands

def build_query(config_file, config_parser):
    mysql_cmds = []
    step_header = StepHeader()
    
    mysql_cmds.extend(step_header.next('select unix_timestamp() ;'))
    mysql_cmds.extend(step_header.next('show databases ;'))
    # get row counts
    for db_name, v in config_parser.items('databases'):
        table_section = TABLE_SECTION_TEMPLATE % db_name
        mysql_cmds.extend(step_header.next('use %s ; ' % db_name))
        for table_name, v in config_parser.items(table_section):
            if not v:
                v = 'id'
            #mysql_cmds.extend(step_header.next('select count(*) from %s ;' % table_name))
            mysql_cmds.extend(step_header.next('select max(%s) from %s ;' % (v, table_name)))

    return '\n'.join(mysql_cmds)

def run_query(query_string, host):
    """
    Run query_string on server specified in host

    Where host is the path to a MySQL 'my.cnf' file with all needed
    connection information including credentials
    """
    arg_list = [
        'mysql',
        '--defaults-file=%s' % host,
        '--batch',
        '--skip-column-names',
        '--force',
        # '--verbose',
        ]
    
    mysql = Popen(arg_list, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    (stdoutdata, stderrdata) = mysql.communicate(query_string)

    if mysql.returncode != 0 or len(stderrdata):
        logging.error("Query Failed %d: '%s'", mysql.returncode,
                stderrdata.strip())

    return stdoutdata

class Step(object):
    table_name_re = re.compile(r'''from (\w+) ;''')
    def __init__(self, line):
        # line is: "Step %d - '<sql stmt> ;'" where last part of
        # statement is table name
        self.step_id = line
        match = self.table_name_re.search(line)
        if match:
            self.table_name = match.group(1)
        else:
            self.table_name = line
        self.lines = []

    def add_line(self, line):
        self.lines.append(line)

    def __getitem__(self, index):
        return self.lines[index]

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        return ((self.step_id == other.step_id) and
                (self.lines == other.lines))

    def __len__(self):
        return len(self.lines)

    def __str__(self):
        return "%s(%d): '%s'" % (self.step_id, len(self),
                                 "'; '".join(self.lines))
    def __repr__(self):
        return '<Step of %d lines>' % len(self)



class StepList(object):
    def __init__(self, data):
        lines = data.split('\n')
        self.host = lines[0]
        steps = []
        step = None
        for l in lines[1:]:
            if len(l) == 0:
                # discard blank lines
                continue
            if l.startswith('Step '):
                step = Step(l)
                steps.append(step)
            else:
                step.add_line(l)
        self.steps = steps

    def __getitem__(self, index):
        return self.steps[index]

    def __len__(self):
        return len(self.steps)

    def __str__(self):
        return self.host

    def __repr__(self):
        return '<StepList %s, %d steps>' % (self.host, len(self))
            
def get_post_key(host1, host2):
    post_key = "%s2%s" % (host1, host2)
    post_key = post_key.replace('.ini', '')
    post_key = post_key.replace('.', '_')
    return post_key

def compare_steps(master, replica):
    logging.info('comparing %r with %r', master, replica)
    post_key = get_post_key(master, replica)
    posts_data = []
    if len(master) != len(replica):
        logging.error("Step count difference: master %d, replica %d",
                len(master), len(replica))
    limit = min(len(master), len(replica))
    total_abs_diff = 0
    for s in range(limit):
        diff_message_template = "%s; replica behind by %d rows"
        m = master[s]
        r = replica[s]
        if m != r:
            # see what changed
            if m.step_id != r.step_id:
                logging.error('Step %d definitions differ; master="%s"; replica="%s"',
                        s+1, m.step_id, r.step_id)
            elif len(m) == len(r) == 1:
                m_rows = int(m[0])
                r_rows = int(r[0])
                diff = m_rows - r_rows
                abs_diff = abs(diff)
                datum_name = m.table_name
                if 'select unix_timestamp()' in m.step_id:
                    # flip sign, so value is delta between sample start,
                    diff = -diff
                    # but don't accumulate to total diff
                    abs_diff = 0
                    # and tweak message
                    diff_message_template = "%s; replica data collected %d seconds later"
                    # and record master time as sample collection time
                    # for graphite
                    posts_data.append((post_key, 'TIMESTAMP', m_rows))
                    datum_name = 'sec_delta'
                posts_data.append((post_key, datum_name, diff))
                total_abs_diff += abs(diff)
                if diff < 0:
                    logging.error("%s; replica has %d more rows "
                            "(%d) than master (%d)", m.step_id,
                            -diff, r_rows, m_rows)
                else:
                    logging.warning(diff_message_template, m.step_id, diff)
            else:
                # more that one row
                if 'show databases' in m.step_id and (len(m) == len(r)+1) and ('mysql' in m):
                    # different permissions on r/o & r/w db's make
                    # 'mysql' database invisible on replica
                    pass
                else:
                    logging.warning("%s; master='%s'; replica='%s'",
                            m.step_id, str(m), str(r))

    logging.info("Total_abs_diff: %d; master='%s'; replica='%s'",
                 total_abs_diff, master, replica)

    posts_data.append((post_key, 'total_abs_diff', total_abs_diff))
    return posts_data

def post_to_history(data):
    logging.error("Posting to graphite not implemented yet")
    time_of_report = data[0][-1]
    lines = []
    for data_point in data[1:]:
        line = GRAPHITE_TEMPLATE % (data_point[0], data_point[1],
                                    data_point[2], time_of_report)
        lines.append(line)
        logging.debug(line)
    message = '\n'.join(lines) + '\n'
    sock.sendall(message)

        

def compare_servers(raw_data, record_data=False):
    if len(raw_data) == 0:
        logging.fatal("No data received")
    else:
        parsed_data = []
        for host, output in raw_data:
            logging.info("parsing data for server: %s" % host)
            details = StepList(output)
            parsed_data.append(details)
        master = parsed_data[0]
        if len(parsed_data) == 1:
            for s in master:
                logging.info(str(s))
        for host in parsed_data[1:]:
            post_data = compare_steps(master, host)
            if record_data:
                post_to_history(post_data)

def process_prior_data(options, args):
    prior_results=[]
    i = 0
    # sigh - some incoming data files will be from multiple queries. The
    # 'adhoc' way to spot the file transitions is by a 2 line pattern:
    #   line 1: file path ending in '.ini'
    #   line 2: Starts with 'Step 1 - '
    # Break each input into those chunks before creating the
    # prior_results elements.
    for f in args:
        i += 1
        i_subfile = 0
        lines = open(f, 'r').readlines()
        subfile_start_line = 0
        cur_line = 2  # we know first 2
        while cur_line < len(lines):
            if (lines[cur_line].startswith('Step 1 - ') and
                lines[cur_line-1].strip().endswith('.ini')):
                # file demarcation at cur_line-1,
                file_boundary_line = cur_line - 1
                data = '\n'.join(lines[subfile_start_line:file_boundary_line])
                prior_results.append(('File %s.%s' % (i, i_subfile), data))
                # update indicies
                subfile_start_line = file_boundary_line
                i_subfile += 1
            cur_line += 1
        # there will always be one inprogress at end
        data = '\n'.join(lines[subfile_start_line:cur_line])
        prior_results.append(('File %s.%s' % (i, i_subfile), data))

    result_code = compare_servers(prior_results, options.record_data)
    return result_code

def main():
    options, args = parse_args()
    # Configure logging
    global logging
    root_log = logging.getLogger()
    log_formatter = logging.Formatter("%(asctime)s - %(message)s")

    if options.logfile:
        import logging.handlers
        # Week one log file per week for 4 weeks
        handler = logging.handlers.TimedRotatingFileHandler(options.logfile,
                                                            when='W6',
                                                            backupCount=4)
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(log_formatter)
    root_log.setLevel(options.loglevel)
    root_log.addHandler(handler)

    if options.record_data:
        # open socket here to avoid "send too soon after open" issue
        # and to allow reuse
        try:
            global sock
            sock = socket.socket()
            sock.connect((GRAPHITE_SERVER, GRAPHITE_PORT) )
        except socket.error:
            msg = ("Couldn't connect to %(server)s on port "
                          "%(port)d, is carbon-cache.py running?" % {
                            'server':GRAPHITE_SERVER, 'port':GRAPHITE_PORT
                          })
            logging.fatal(msg)
            raise SystemExit(msg)

    result_code = 0  # assume success
    if options.process_only:
        result_code = process_prior_data(options, args)
    else:
        # run live query
        from ConfigParser import SafeConfigParser
        # Load options from config if it's set
        if options.config_file:
            config_parser = SafeConfigParser()
            config_parser.read([options.config_file])

        query = build_query(options.config_file, config_parser)
        result_data = []
        for server in args:
            results = run_query(query, server)
            result_data.append((server, results))
            if not options.compare:
                print(server)
                print(results)

        if options.compare:
            result_code = compare_servers(result_data, options.record_data)
    return result_code
        

if __name__ == '__main__':
    raise SystemExit(main())
