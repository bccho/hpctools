import subprocess
import json
from time import time, sleep
import logging


class SLURMCluster:
    """ Session manager for interacting with a SLURM-based cluster over SSH.
    
    Note: For authentication, generate a private/public key (e.g., with ssh-keygen) 
          and copy public key to "~/.ssh/authorized_keys" on cluster.
    """
    def __init__(self, host, user):
        """ Initializes session parameters.
        
        Args:
            host: cluster address
            user: username for authentication
        """
        self.host = host
        self.user = user
        
        
    def run_cmd(self, cmd, encoding="utf-8"):
        """ Runs commands over ssh and returns output. """

        # Concatenate multiple commands (lines)
        if type(cmd) == list:
            cmd = " && ".join(cmd)

        # Call ssh with auth and commands
        proc = subprocess.run(["ssh", self.user + "@" + self.host, cmd],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              encoding=encoding)

        # Return outputs
        return proc.stdout
    
    def submit_job(self, script_path, script_args=[], working_directory="$HOME"):
        """ Submits a job via sbatch and returns the job ID. """
        
        if type(script_args) == list:
            script_args = " ".join(script_args)
            
        out = self.run_cmd([
            "cd \"%s\"" % working_directory,
            "sbatch " + script_path + " " + script_args
        ])
        
        if not "Submitted batch job" in out:
            # TODO: raise exception
            logging.error("Failed to submit job: " + out)
            return None
        
        # Get job ID from output and return
        return out.split()[-1]
    
    def cancel_job(self, job_id):
        """ Cancels a job via scancel. """
        self.run_cmd("scancel %s" % job_id)
    
    def get_job_state(self, job_id, compact=False):
        """ Returns job status code or None if does not exist. 
        
        Status codes (from `man squeue`):
            (short code) 
            (BF) BOOT_FAIL: Job terminated due to launch failure, typically due to a hardware failure (e.g. unable to boot the node or block and the job can not be requeued).
            (CA) CANCELLED: Job was explicitly cancelled by the user or system administrator. The job may or may not have been initiated.
            (CD) COMPLETED: Job has terminated all processes on all nodes with an exit code of zero.
            (CF) CONFIGURING: Job has been allocated resources, but are waiting for them to become ready for use (e.g. booting).
            (CG) COMPLETING: Job is in the process of completing. Some processes on some nodes may still be active.
            (DL) DEADLINE: Job terminated on deadline.
            (F) FAILED: Job terminated with non-zero exit code or other failure condition.
            (NF) NODE_FAIL: Job terminated due to failure of one or more allocated nodes.
            (OOM) OUT_OF_MEMORY: Job experienced out of memory error.
            (PD) PENDING: Job is awaiting resource allocation.
            (PR) PREEMPTED: Job terminated due to preemption.
            (R) RUNNING: Job currently has an allocation.
            (RD) RESV_DEL_HOLD: Job is held.
            (RF) REQUEUE_FED: Job is being requeued by a federation.
            (RH) REQUEUE_HOLD: Held job is being requeued.
            (RQ) REQUEUE: Completing job is being requeued.
            (RS) RESIZING: Job is about to change size.
            (RV) REVOKED: Sibling was removed from cluster due to other cluster starting the job.
            (S) SUSPENDED: Job has an allocation, but execution has been suspended and CPUs have been released for other jobs.
            (SE) SPECIAL_EXIT: The job was requeued in a special state. This state can be set by users, typically in EpilogSlurmctld, if the job has terminated with a particular exit value.
            (SI) SIGNALING: Job is being signaled.
            (ST) STOPPED: Job has an allocation, but execution has been stopped with SIGSTOP signal. CPUS have been retained by this job.
            (TO) TIMEOUT: Job terminated upon reaching its time limit.
        """
        
        code = "state"
        if compact:
            code = "statecompact"
        
        # Query squeue for state
        out = self.run_cmd('squeue -j %s --Format="%s"' % (str(job_id), code))
        
        # Check if job exists
        if "slurm_load_jobs error: Invalid job id specified" in out:
            return None
        
        return out.splitlines()[-1].strip()
    
    def job_info(self, job_id):
        """ Returns squeue info about a job or None if it does not exist. 
        See `man squeue` for possible fields. """
        
        # Query squeue for all available info
        out = self.run_cmd("squeue -j " + str(job_id) + " --format="+'"%all"')
        
        # Check if job exists
        if "slurm_load_jobs error: Invalid job id specified" in out:
            return None
        
        # Split output into cells
        fields, vals = [row.split("|") for row in out.splitlines()]
        
        # Return dictionary from filtered job data
        return {k: v for k,v in zip(fields, vals) if len(k) > 0}
    
    def wait_for_job(self, job_id, timeout=60, poll_interval=1, verbose=True):
        """ Blocks until job starts running.
        Args:
            job_id: SLURM job ID (str or int)
            timeout: seconds before returning or None to wait indefinitely (default: 60)
            poll_interval: seconds between polling (default: 1)
            verbose: print status messages (default: True)
            
        Returns:
            is_running: True if the job started running, False if timed out
            total_time_elapsed: total seconds spent waiting
            """
        
        if verbose:
            print("Waiting for job %s... " % str(job_id), end="", flush=True)
        
        t0 = time()
        done = False
        while not done:
            # Poll for job state
            t0_poll = time()
            is_running = self.job_state(job_id) == "RUNNING"
            
            # Compute timing
            poll_elapsed = time() - t0_poll
            total_time_elapsed = time() - t0
            
            # Check for timeout
            timed_out = timeout is not None and (time() - t0) >= timeout
            
            # Should we stop?
            done = is_running or timed_out
            
            if not done:
                # Compute poll interval remaining
                interval_remaining = max([poll_interval - poll_elapsed, 0])

                # Wait
                sleep(interval_remaining)
        
        if verbose:
            if is_running:
                print("Running after %.1f seconds." % total_time_elapsed)
            elif timed_out:
                print("Timed out after %.1f seconds." % total_time_elapsed)
            else:
                print("Failed to run after %.1f seconds." % total_time_elapsed)
        
        return is_running, total_time_elapsed
        
    
    