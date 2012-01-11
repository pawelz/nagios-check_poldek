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
import re
import subprocess

__version__ = "0.6"
__copyright__ = "2009, 2010 TouK sp. z o.o. s.k.a; 2012 Elan Ruusamäe"

CONFIG = {
    "errorLevel": 10,
    "warningLevel": 5,
    "verbose": False,
    "sources": [],
    "cache": "/tmp/check_poldek",
    "extraArgs": [],
}

RESULT = {"OK": 0, "WARNING": 1, "ERROR": 2}

# Functions
def version():
    """
    print plugin version and copyright
    """

    print "check_poldek v. " + __version__ + " Copyright (c) " + __copyright__

def usage():
    """
    print version and usage
    """

    print
    version()
    print
    print "Usage:"
    print "  check_poldek [-w WARN] [-c ERROR] [--cache DIRECTORY]"
    print "               [-- arguments passed to poldek]"
    print "  check_poldek --help"
    print "  check_poldek --version"
    print

def finish(code, message):
    """
    print status message and exit
    """

    print "POLDEK " + code+ ": " + message.splitlines()[0]
    sys.exit(RESULT[code])

def parseopts():
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

def update_indexes():
    """
    sync indexes; abort on errors
    """

    # sync indexes
    command = ["poldek", "--cache", CONFIG["cache"], "-q", "--up"] \
        + CONFIG["extraArgs"]
    if (CONFIG["verbose"]):
        print >> sys.stderr, "executing: %s" % " ".join(command)
    ret = subprocess.call(command, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    if ret < 0:
        finish("ERROR", "Could not update poldek indices: Killed by " + str(-ret) + " signal.")
    if ret > 0:
        finish("ERROR", "Could not update poldek indices: Poldek exited with " + str(ret) + ".")

def check_updates():
    """
    invoke --upgrade-dist
    return output lines as array
    """

    command = ["poldek", "--cache", CONFIG["cache"], "-t", "--noask", "--upgrade-dist"] + CONFIG["extraArgs"]
    if CONFIG["verbose"]:
        print >> sys.stderr, "executing: %s" % " ".join(command)
    proc = subprocess.Popen(command, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

    r_error = re.compile("^error: (.*)$")
    r_warn = re.compile("^warn: (.*)$")
    r_result = re.compile("^There[^0-9]* ([0-9]+) package.* to remove:$")

    n_errors = 0
    n_warnings = 0
    n_packages = 0
    status_line = "System is up-to-date."

    # Iterate through lines of poldek output
    for line in proc.stdout:
        line = line.rstrip()

        if (CONFIG["verbose"]):
            print >> sys.stderr, "stdout: %s" % line

        match = r_error.match(line)
        if (match):
            if (CONFIG["verbose"]):
                print >> sys.stderr, "ERROR: %s" % line
            n_errors += 1
            lasterror = match.group(1)

        match = r_warn.match(line)
        if (match):
            if (CONFIG["verbose"]):
                print >> sys.stderr, "WARNING: %s " % line
            n_warnings += 1
            lastwarn = match.group(1)

        match = r_result.match(line)
        if (match):
            n_packages = int(match.group(1))
            status_line = line

    ret = proc.wait()
    if ret < 0:
        finish("ERROR", "Could not run poldek: Killed by " + str(-ret) + " signal.")

    if n_errors > 0:
        warning_msg = ""
        if n_warnings > 0:
            warning_msg = " and " + str(n_warnings) + " poldek warnings."
        finish("ERROR", str(n_errors) + " poldek errors: " + lasterror + warning_msg)

    if n_packages >= CONFIG["errorLevel"]:
        finish("ERROR", status_line)

    if ret > 0:
        finish("ERROR", "Could not run poldek: Poldek exited with " + str(ret) + ".")

    if n_warnings > 0:
        finish("WARNING", str(n_warnings) + " poldek warnings: " + lastwarn)

    if n_packages >= CONFIG["warningLevel"]:
        finish("WARNING", status_line)

    finish("OK", status_line)

parseopts()
update_indexes()
check_updates()
