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

ver = "0.6"
copyright = "2009, 2010 TouK sp. z o.o. s.k.a; 2012 Elan Ruusamäe"

config = {
    "errorLevel": 10,
    "warningLevel": 5,
    "verbose": False,
    "sources": [],
    "cache": "/tmp/check_poldek",
    "extraArgs": [],
}

result = {"POLDEK OK": 0, "POLDEK WARNING": 1, "POLDEK ERROR": 2}

# Functions
def version():
    print "check_poldek v. " + ver + " Copyright (c) " + copyright

def usage():
    print
    version()
    print
    print "Usage:"
    print "  check_poldek [-w WARN] [-c ERROR] [--cache DIRECTORY]"
    print "               [-- arguments passed to poldek]"
    print "  check_poldek --help"
    print "  check_poldek --version"
    print

def finish(rv, line):
    print rv + ": " + line.splitlines()[0]
    sys.exit(result[rv])

for n in range(len(sys.argv)):
    if sys.argv[n] == "--help":
        usage()
        sys.exit()
    if sys.argv[n] == "--version":
        version()
        sys.exit()
    if sys.argv[n] == "-v":
        config["verbose"] = True
    if sys.argv[n] == "-c":
        config["errorLevel"] = int(sys.argv[n+1])
    if sys.argv[n] == "-w":
        config["warningLevel"] = int(sys.argv[n+1])
    if sys.argv[n] == "--cache":
        config["cache"] = sys.argv[n+1]
    if sys.argv[n] == "--sn" or sys.argv[n] == "-n":
        config["sources"].extend(sys.argv[n+1].split(','))
    if sys.argv[n] == "--":
        config["extraArgs"] = sys.argv[n+1:]
        break

for n in config["sources"]:
    config["extraArgs"].extend(['-n', n])

# sync indexes
command = ["poldek", "--cache", config["cache"], "-q", "--up"] + config["extraArgs"]
if (config["verbose"]):
    print >> sys.stderr, "executing: %s" % " ".join(command)
rv = subprocess.call(command, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
if rv < 0:
    finish("POLDEK ERROR", "Could not update poldek indices: Killed by " + str(-rv) + " signal.")
if rv > 0:
    finish("POLDEK ERROR", "Could not update poldek indices: Poldek exited with " + str(rv) + ".")

# invoke --upgrade-dist
command = ["poldek", "--cache", config["cache"], "-t", "--noask", "--upgrade-dist"] + config["extraArgs"]
if config["verbose"]:
    print >> sys.stderr, "executing: %s" % " ".join(command)
p = subprocess.Popen(command, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

reError = re.compile("^error: (.*)$")
reWarn = re.compile("^warn: (.*)$")
reResult = re.compile("^There[^0-9]* ([0-9]+) package.* to remove:$")

numberOfErrors = 0
numberOfWarns = 0
numberOfPackages = 0
resultLine = "System is up-to-date."

# Iterate through lines of poldek output
for line in p.stdout:
    line = line.rstrip()

    if (config["verbose"]):
        print >> sys.stderr, "stdout: %s" % line

    m = reError.match(line)
    if (m):
        if (config["verbose"]):
            print >> sys.stderr, "ERROR: %s" % line
        numberOfErrors += 1
        lasterror = m.group(1)

    m = reWarn.match(line)
    if (m):
        if (config["verbose"]):
            print >> sys.stderr, "WARNING: %s " % line
        numberOfWarns += 1
        lastwarn = m.group(1)

    m = reResult.match(line)
    if (m):
        numberOfPackages = int(m.group(1))
        resultLine = line

rv = p.wait()
if rv < 0:
    finish("POLDEK ERROR", "Could not run poldek: Killed by " + str(-rv) + " signal.")

if numberOfErrors > 0:
    warning_msg = ""
    if numberOfWarns > 0:
        warning_msg = " and " + str(numberOfWarns) + " poldek warnings."
    finish("POLDEK ERROR", str(numberOfErrors) + " poldek errors: " + lasterror + warning_msg)

if numberOfPackages >= config["errorLevel"]:
    finish("POLDEK ERROR", resultLine)

if rv > 0:
    finish("POLDEK ERROR", "Could not run poldek: Poldek exited with " + str(rv) + ".")

if numberOfWarns > 0:
    finish("POLDEK WARNING", str(numberOfWarns) + " poldek warnings: " + lastwarn)

if numberOfPackages >= config["warningLevel"]:
    finish("POLDEK WARNING", resultLine)

finish("POLDEK OK", resultLine)
