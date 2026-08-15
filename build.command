#!/bin/bash
# ============================================================================
# Double-click launcher for build.sh
# ============================================================================
# Finder runs a .command file in Terminal, which is the only way to start a
# build without opening a shell first. build.sh itself stays a plain .sh so it
# can be called normally from CI and from the command line.
#
# Finder launches this from an arbitrary working directory, so the cd below is
# load-bearing, not tidiness.
#
# Pass an argument by editing the line below, or run ./build.sh installer from
# a terminal. A .command file cannot take arguments from a double-click.
# ============================================================================

cd "$(dirname "$0")"

./build.sh installer
STATUS=$?

echo ""
if [ $STATUS -eq 0 ]; then
    echo "Build finished."
else
    echo "Build FAILED (exit $STATUS). The error is above."
fi

# Without this the Terminal window closes the instant the build ends, taking
# the output with it — including whatever went wrong.
echo "Press any key to close..."
read -n 1 -s
