# hpctools

This package provides a set of utilities for interacting with the SLURM job scheduler on an HPC cluster through Python (over ssh).

**Note on authentication:** Currently, password-based auth functionality is not provided. This is intended to encourage use of SSH keys so as to avoid having plain-text passwords in code. See [`ssh-keygen`](https://linux.die.net/man/1/ssh-keygen) for documentation on how to generate a key (or use PuTTYgen on Windows).

## Basic usage
```python
import hpctools

# Create session to store auth for ssh
cluster = hpctools.SLURMCluster(host="tigergpu.princeton.edu", user="tdp")

# Evaluate a series of shell commands and return the output
print(cluster.run_cmd([
    "mkdir test_dir",
    "cd test_dir",
    "touch file_test",
    "ls -lh",
    "cd ..",
    "rm -rf test_dir"]))
```

**Outputs:**
```
total 0
-rw-r--r--. 1 tdp pni 0 Mar  2  2018 file_test
```


## Submitting and checking on a job
```python
# Submit a bash script with SLURM directives via sbatch
job_id = cluster.submit_job("test_job.sh", 
    script_args=["arg1", "arg2"], # command line arguments passed to the script
    working_directory="$HOME/lab/code/hpctools/slurm_scripts") # starting directory

# Block until job starts
is_running, time_elapsed = cluster.wait_for_job(job_id, timeout=120, poll_interval=2)

# Print job metadata
from hpctools.utils import print_dict
print_dict(cluster.job_info(job_id))
```

**Outputs:**
```
/var/spool/slurmd/job435117/slurm_script arg1 arg2
Ran test_job (job ID: 435117) at Sun Mar  4 21:02:43 EST 2018.
[Sun Mar  4 21:02:58 EST 2018] Exiting...
```
