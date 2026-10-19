import argparse
import importlib.metadata
import numpy as np
import os
import platform as platform_
import yaml
import subprocess

from pathlib import Path

# Supported compute platforms and their parameters
PLATFORMS = ["dane", "lassen", "tuolumne"]
#
JOB_SUBMISSION = {}
JOB_SUBMISSION["dane"] = "sbatch"
JOB_SUBMISSION["lassen"] = "bsub"
JOB_SUBMISSION["tuolumne"] = "flux batch"
#
JOB_SCHEDULER = {}
JOB_SCHEDULER["dane"] = "slurm"
JOB_SCHEDULER["lassen"] = "lsf"
JOB_SCHEDULER["tuolumne"] = "flux"
#
JOB_TIME = {}
JOB_TIME["dane"] = "24:00:00"
JOB_TIME["lassen"] = "12:00"
JOB_TIME["tuolumne"] = "24h"

# ======================================================================================
# Run options
# ======================================================================================

parser = argparse.ArgumentParser(description="MC/DC Profiling Test Suite - Serial")
parser.add_argument("--platform", type=str, required=True, choices=PLATFORMS)
parser.add_argument("--save_recent_output", default=False, action="store_true")
parser.add_argument("--name", type=str, default="ALL", help="Name of the task to run")
parser.add_argument(
    "--N_particle",
    type=lambda x: int(float(x)),
    default=None,
    help="Number of particles (overrides the task list)",
)
parser.add_argument(
    "--Time", type=str, default=None, help="Job time (overrides the platform default)"
)
parser.add_argument(
    "--output_folder",
    default=False,
    action="store_true",
    help="Save the profiling results to a top-level output folder",
)
args, unargs = parser.parse_known_args()

# Set platform parameters
platform = args.platform
job_submission = JOB_SUBMISSION[platform]
job_scheduler = JOB_SCHEDULER[platform]
job_time = JOB_TIME[platform] if args.Time is None else args.Time

# If --output_folder is set, create a top-level folder "output"
output_dir = os.path.join(os.getcwd(), "output")
if args.output_folder:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

# Get the PBS template
with open("pbs_templates/%s.pbs" % job_scheduler, "r") as f:
    pbs_template = f.read()


# ======================================================================================
# Preparation
# ======================================================================================

# Create version result to store the results
version = importlib.metadata.version("mcdc")
dir_version = "%s" % version
Path(dir_version).mkdir(parents=True, exist_ok=True)

# Create and get in to the folder
dir_serial = "%s/serial/%s" % (version, platform)
Path(dir_serial).mkdir(parents=True, exist_ok=True)
os.chdir(dir_serial)

# Save the machine specification
spec = {}
spec["architecture"] = str(platform_.architecture())
spec["machine"] = str(platform_.machine())
spec["node"] = str(platform_.node())
spec["platform"] = str(platform_.platform(aliased=True))
spec["processor"] = str(platform_.processor())
spec["release"] = str(platform_.release())
spec["system"] = str(platform_.system())
spec["version"] = str(platform_.version())
with open("machine_spec.yaml", "w") as f:
    yaml.dump(spec, f)

# Read the tasks
os.chdir("../../../")
with open("tasks/serial.yaml", "r") as file:
    tasks = yaml.safe_load(file)

# Check if specified --name is listed in the task
if args.name != "ALL" and args.name not in tasks:
    print(f"[ERROR] Specified problem name {args.name} is not in the task list.")
    exit()

# ======================================================================================
# Run the tests
# ======================================================================================

# Loop over the test suite problems
os.chdir("test_suite")
for problem in tasks:
    # If --name is specified, skip other problems
    if args.name != "ALL" and problem != args.name:
        continue

    # Get into the problem folder
    os.chdir(problem)

    # Create and get into output folder
    Path("output").mkdir(parents=True, exist_ok=True)
    os.chdir("output")

    # Loop over methods
    for method in tasks[problem]:
        # Loop over modes
        for mode in tasks[problem][method]:
            # Create and get into sub output folder
            dir_output = "serial-%s-%s-%s" % (platform, method, mode)
            Path(dir_output).mkdir(parents=True, exist_ok=True)
            os.chdir(dir_output)

            # Copy necessary files
            subprocess.run("cp ../../* . 2>/dev/null", shell=True)

            # Start building the PBS file
            pbs_text = pbs_template[:]
            pbs_text = pbs_text.replace("<N_NODE>", "1")
            pbs_text = pbs_text.replace(
                "<JOB_NAME>", "mcdc-ser-%s-%s-%s" % (problem, method, mode)
            )
            pbs_text = pbs_text.replace("<TIME>", job_time)
            pbs_text = pbs_text.replace("<CASE>", "")

            # Run parameters
            start, stop, num = tasks[problem][method][mode]
            if args.N_particle is not None:
                N_list = [args.N_particle]
            else:
                N_list = np.logspace(start, stop, num, dtype=int)

            # Loop over runs
            commands = ""
            previous_output = None
            for N in N_list:
                # Profiling result file name (without extension)
                profile = "profile_%i" % N
                if args.output_folder:
                    profile = os.path.join(
                        output_dir, "profile_%s-%s-%s_%i" % (problem, method, mode, N)
                    )

                # Profiler: cProfile for Python mode, profila for Numba mode
                #   (profila sets NUMBA_DEBUGINFO=1 itself; the local cache dir
                #    prevents reusing cached code compiled without debug info)
                if mode == "python":
                    profiler = "python -m cProfile -o %s.prof" % profile
                else:
                    profiler = (
                        "NUMBA_CACHE_DIR=numba_cache python -m profila annotate --"
                    )
                commands += (
                    "%s input.py %s --mode=%s --N_particle=%i --output=output_%i --no-progress_bar --caching --runtime_output"
                    % (profiler, method, mode, N, N)
                )
                if mode == "python":
                    commands += (
                        "\ngprof2dot -f pstats --colour-nodes-by-selftime %s.prof | dot -Tpng -o %s.png\n"
                        % (profile, profile)
                    )
                else:
                    commands += " > %s.txt\n" % profile

                # Delete previous output (note that runtimes are saved)
                if previous_output is not None:
                    commands += "rm %s.h5\n" % previous_output

                previous_output = "output_%i" % N
            # Delete recent output?
            if not args.save_recent_output:
                commands += "rm %s.h5\n" % previous_output

            # Finalize commands and PBS file
            pbs_text = pbs_text.replace("<COMMANDS>", commands)
            with open(f"submit.pbs", "w") as f:
                f.write(pbs_text)

            # Submit job
            subprocess.run("%s submit.pbs" % job_submission, shell=True, check=True)

            os.chdir("..")
    os.chdir("../../")
