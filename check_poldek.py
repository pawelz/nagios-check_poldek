#!/usr/bin/python
# vim:fileencoding=utf-8

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Copyright (c) 2009, 2010 TouK sp. z o.o. s.k.a.
# Author: Paweł Zuzelski <pzz@touk.pl>
# Copyright (c) 2012 Elan Ruusamäe <glen@pld-linux.org>

import sys
import subprocess

__version__ = "0.7"
__copyright__ = "2009, 2010 TouK sp. z o.o. s.k.a; 2012 Elan Ruusamäe"

CONFIG = {
    "warningLevel": 5,
    "errorLevel": 10,
    "verbose": False,
    "sources": [],
    "cache": "/tmp/check_poldek",
    "extraArgs": [],
}

RESULT = {"OK": 0, "WARNING": 1, "ERROR": 2, "CRITICAL": 2, "UNKNOWN": 3}

# Functions
def version():
    """
    print plugin version and copyright
    """

    print "check_poldek v" + __version__ + " Copyright (c) " + __copyright__

def usage():
    """
    print version and usage
    """

    print
    version()
    print
    print "Usage:"
    print "  check_poldek [-w WARN] [-c ERROR] [--cache DIRECTORY]"
    print "               [-n, --sn NAME]"
    print "               [-- arguments passed to poldek]"
    print "  check_poldek --help"
    print "  check_poldek --version"
    print

def die(code, message):
    """
    print status message and exit
    """

    print "POLDEK " + code + ": " + message
    sys.exit(RESULT[code])

def parseopts():
    """
    parse commandline options, setup them to CONFIG global
    """
    for arg in range(len(sys.argv)):
        if sys.argv[arg] == "--help":
            usage()
            sys.exit()
        if sys.argv[arg] == "--version":
            version()
            sys.exit()
        if sys.argv[arg] == "-v":
            CONFIG["verbose"] = True
        if sys.argv[arg] == "-c":
            CONFIG["errorLevel"] = int(sys.argv[arg + 1])
        if sys.argv[arg] == "-w":
            CONFIG["warningLevel"] = int(sys.argv[arg + 1])
        if sys.argv[arg] == "--cache":
            CONFIG["cache"] = sys.argv[arg + 1]
        if sys.argv[arg] == "--sn" or sys.argv[arg] == "-n":
            CONFIG["sources"].extend(sys.argv[arg + 1].split(','))
        if sys.argv[arg] == "--":
            CONFIG["extraArgs"] = sys.argv[arg + 1:]
            break

    for arg in CONFIG["sources"]:
        CONFIG["extraArgs"].extend(['-n', arg])

def poldek(args):
    """
    invoke poldek
    enforces cachedir
    applies extraArgs from plugin commandline
    appends args passed as function args
    """

    command = ["poldek", "-q", "--cache", CONFIG["cache"]]
    command.extend(CONFIG["extraArgs"])
    command.extend(args)

    if (CONFIG["verbose"]):
        print >> sys.stderr, "executing: %s" % " ".join(command)

    proc = subprocess.Popen(command, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    stdout = proc.stdout
    ret = proc.wait()
    return (ret, stdout)

def update_indexes():
    """
    sync indexes; abort on errors
    """

    # sync indexes
    (ret, stdout) = poldek(["--up"])
    if ret < 0:
        die("ERROR", "Could not update poldek indices: Killed by " + str(-ret) + " signal.")
    if ret > 0:
        print "\n".join(stdout)
        die("ERROR", "Could not update poldek indices: Poldek exited with " + str(ret) + ".")

def check_updates():
    """
    invoke --upgrade-dist
    return output lines as array
    """

    update_indexes()

    # check security updates
    (ret, stdout) = poldek(["--cmd", "ls -S --qf '%{N}\n'"])
    if ret < 0:
        die("ERROR", "Could not run poldek: Killed by " + str(-ret) + " signal.")
    if ret > 0:
        die("ERROR", "Could not run poldek: Poldek exited with " + str(ret) + ".")

    pkgs_security = []
    for line in stdout:
        line = line.rstrip()
        if (CONFIG["verbose"]):
            print >> sys.stderr, "stdout: %s" % line
        pkgs_security.append(line)

    # check plain updates
    (ret, stdout) = poldek(["--cmd", "ls -u --qf '%{N}\n'"])
    if ret < 0:
        die("ERROR", "Could not run poldek: Killed by " + str(-ret) + " signal.")
    if ret > 0:
        die("ERROR", "Could not run poldek: Poldek exited with " + str(ret) + ".")

    pkgs_update = []
    for line in stdout:
        line = line.rstrip()
        if (CONFIG["verbose"]):
            print >> sys.stderr, "stdout: %s" % line
        pkgs_update.append(line)

    status_line = []
    status_code = "UNKNOWN"

    # security updates mark always critical
    if len(pkgs_security):
        status_line.append("%d security updates (%s)" % (len(pkgs_security), ", ".join(pkgs_security)))
        status_code = "CRITICAL"

    n_pkgs_update = len(pkgs_update)
    if n_pkgs_update == 0:
		# security updates always present in normal update list too
        status_code = "OK"
        status_line.append("No updates")
    else:
        if n_pkgs_update > CONFIG["errorLevel"]:
            status_code = "CRITICAL"
        elif n_pkgs_update > CONFIG["warningLevel"]:
            if not status_code == "CRITICAL":
                status_code = "WARNING"
        else:
            if not status_code == "CRITICAL":
                status_code = "OK"

        status_line.append("%d updates pending" % n_pkgs_update)

    die(status_code, "; ".join(status_line))

parseopts()
check_updates()
die("UNKNOWN", "Unkown result")
