##
## ooo_handler.py
## Login : <uli@pu.smp.net>
## Started on  Fri Mar 14 14:05:51 2008 Uli Fouquet
## $Id$
## 
## Copyright (C) 2008 Uli Fouquet
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##
"""
Start/stop a locally installed OpenOffice.org server instance.

This script requires (beside an installed OOo server) a running X
server.

Many code inhere is stolen from the cookbook:

  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012

Changes were made to handle whole process groups instead of single
processes.

"""
import sys
import os
import time
from optparse import OptionParser
from signal import SIGTERM


OOO_BINARY = '/usr/lib/openoffice/program/soffice'
PIDFILE = '/tmp/ooodaeomon.pid'

def run(cmd):
    pass

def daemonize(stdout='/dev/null', stderr=None, stdin='/dev/null',
              pidfile=None, startmsg = 'started with pid %s' ):
    
    try: 
        pid = os.fork() 
        if pid > 0:
            # exit first parent
            sys.exit(0) 
    except OSError, e: 
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/") 
    os.setsid() 
    os.umask(0) 

    # do second fork
    try: 
        pid = os.fork() 
        if pid > 0:
            # exit from second parent, print eventual PID before
            sys.exit(0) 
    except OSError, e: 
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1)
        
    if (not stderr):
	stderr = stdout

    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    pid = str(os.getpgrp())
    sys.stderr.write("\n%s\n" % startmsg % pid)
    sys.stderr.flush()
    if pidfile: file(pidfile,'w+').write("%s\n" % pid)

    
    # Standard Ein-/Ausgaben auf die Dateien umleiten
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def startstop(stdout='/dev/null', stderr=None, stdin='/dev/null',
              pidfile='pid.txt', startmsg = 'started with pid %s',
              action='start' ):
    if action:
        try:
            pf  = file(pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
         
        if 'stop' == action or 'restart' == action:
            if not pid:
                mess = "Could not stop, pid file '%s' missing.\n"
                sys.stderr.write(mess % pidfile)
                if 'stop' == action:
                    sys.exit(1)
                action = 'start'
                pid = None
            else:
               try:
                  sys.stderr.write("stopping pid %s..." % pid)
                  while 1:
                      os.killpg(pid,SIGTERM)
                      time.sleep(1)
               except OSError, err:
                  err = str(err)
                  if err.find("No such process") > 0:
                      os.remove(pidfile)
                      sys.stderr.write(" done.\n")
                      if 'stop' == action:
                          sys.exit(0)
                      action = 'start'
                      pid = None
                  else:
                      print str(err)
                      sys.exit(1)
        
        if 'start' == action:
            if pid:
                mess = "Start aborted since pid file '%s' exists.\n"
                sys.stderr.write(mess % pidfile)
                sys.exit(1)

            sys.stderr.write("starting OpenOffice.org server, ")
            sys.stderr.write("going into background...")
            daemonize(stdout,stderr,stdin,pidfile,startmsg)
            return

        if 'status' == action:
            if not pid:
                sys.stderr.write('Status: Stopped\n')

            else: sys.stderr.write('Status: Running (PID %s) \n'%pid)
            sys.exit(0)



def start(binarypath):
    cmd = "%s %s %s" % (
        binarypath,
        '"-accept=socket,host=localhost,port=2002;urp;"',
        '-headless -nologo -nofirststartwizard -norestore')
    os.system(cmd)

def getOptions():
    usage = "usage: %prog [options] start|stop|restart|status"
    allowed_args = ['start', 'stop', 'restart', 'status']
    parser = OptionParser(usage=usage)

    parser.add_option(
        "-b", "--binarypath",
        help = "absolute path to OpenOffice.org binary. This option "
               "makes only sense when starting the daemon. Default: %s" %
        OOO_BINARY,
        default = OOO_BINARY,
        )

    parser.add_option(
        "-p", "--pidfile",
        help = "absolute path of PID file. Default: %s" % PIDFILE,
        default = PIDFILE,
        )

    parser.add_option(
        "--stdout", metavar='FILE',
        help = "file where daemon messages should be logged. "
               "Default: /dev/null",
        default = '/dev/null',
        )

    parser.add_option(
        "--stderr", metavar='FILE',
        help = "file where daemon errors should be logged. "
               "If not set (default) stdout is used.",
        default = None,
        )

    parser.add_option(
        "--stdin", metavar='FILE',
        help = "file where daemon input is read from. "
               "Default: /dev/null",
        default = None,
        )

    
    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error("only one argument allowed. Use option '-h' for help.")

    if not os.path.isfile(options.binarypath):
        parser.error("no such file: %s. Use -b to set the binary path. "
                     "Use -h to see all options." % options.binarypath)
        
    cmd = None
    if len(args) == 1:
        cmd = args[0]
    if cmd not in allowed_args:
        parser.error("argument must be one of %s. Use option '-h' for help." %
                     ', '.join(["'%s'" % x for x in allowed_args]))
    return (cmd, options)
    
    
def main(argv=sys.argv):
    if os.name != 'posix':
        print "This script only works on POSIX compliant machines."
        sys.exit(-1)
        
    (cmd, options) = getOptions()

    # startstop() returns only in case of 'start' or 'restart' cmd...
    startstop(stderr=options.stderr, stdout=options.stdout,
              pidfile=options.pidfile, action=cmd)
    start(options.binarypath)

    sys.exit(0)
