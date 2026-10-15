#!/usr/bin/env python3
"""Compile a probe with the exact kernel flags recorded by Kbuild.

Usage: compile-layout.py patched-out baseline-out baseline-include destination
baseline-include/linux/sched.h must contain the original unpatched header.
The baseline-out must be prepared from the original kernel configuration.
Run with the same compiler PATH used by the kernel build.
"""
from pathlib import Path
import shlex
import subprocess
import sys

patched_out, baseline_out, baseline_include, destination = (
    Path(p).resolve() for p in sys.argv[1:])
destination.mkdir(parents=True, exist_ok=True)
probe = Path(__file__).with_name('layout-probe.c').resolve()
line = (patched_out / 'init/.init_task.o.cmd').read_text().splitlines()[0]
args = shlex.split(line.split(' := ', 1)[1])
args = [arg for arg in args if not arg.startswith('-Wp,-MMD,')]
args[args.index('-o') + 1] = str(destination / 'layout-patched.o')
args[-1] = str(probe)
subprocess.run(args, cwd=patched_out, check=True)
args[args.index('-o') + 1] = str(destination / 'layout-baseline.o')
args.insert(1, '-I' + str(baseline_include))
subprocess.run(args, cwd=baseline_out, check=True)
