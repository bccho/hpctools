import subprocess
import json
from time import time, sleep
import logging
import psutil

from .ssh import SLURMCluster


class JupyterCluster(SLURMCluster):
    """ Manages Jupyter Lab notebook server jobs that are forwarded over reverse SSH. """
    
    def __init__(self, host, user, job_port=9010,
            slurm_scripts_path="$HOME/lab/code/hpctools/slurm_scripts",
            env_name=None):
        """
        Args:
            host: cluster address
            user: username for authentication
            slurm_scripts_path: relative path to directory containing SLURM utility scripts
        """
        super().__init__(host, user)
        self.slurm_scripts_path = slurm_scripts_path
        self.job_port = str(job_port)
        self.env_name = env_name
        self.metadata = None
    
    def get_notebook_metadata(self):
        """ Returns Jupyter Notebook job metadata from generated JSON file. """
        
        # Get metadata file contents over ssh
        out = self.run_cmd([
            "cd " + self.slurm_scripts_path,
            "cat jupyter_lab." + self.job_port + ".json"
        ])
        
        try:
            # Parse json
            self.metadata = json.loads(out)
        except:
            # Couldn't parse the JSON (possibly the file doesn't exist)
            self.metadata = None

        return self.metadata

        
    def is_notebook_running(self, update_metadata=True):
        """ Returns True if there is an running job for a given notebook port. """
        
        # Check job metadata
        if update_metadata or self.metadata is None:
            meta = self.get_notebook_metadata()
        
        # Check if job is running through SLURM
        is_running = False
        if self.metadata is not None:
            is_running = self.get_job_state(self.metadata["job_id"]) == "RUNNING"
        
        return is_running
        
    
    def start_notebook(self, job_script="jupyter_lab_gpu.sh", restart=False, wait_for_job_start=False, start_tunnel=True):
        """ Starts a notebook job for a given port if one isn't currently running. """
        
        # Check if notebook job is already running on the cluster
        already_running = self.is_notebook_running()

        if already_running:
            if restart:
                # Cancel existing job
                print("Stopping existing notebook (job id: %s)..." % self.metadata["job_id"])
                self.cancel_job(self.metadata["job_id"])
            else:
                # Running job already exists, so just quit
                print("Notebook at port %s is already running (job id: %s)." % (self.job_port, self.metadata["job_id"]))
                return None
                
        # Submit job
        script_args = [self.job_port]
        if self.env_name is not None:
            script_args.append(self.env_name)
        job_id = self.submit_job(
            script_path=job_script,
            script_args=script_args,
            working_directory=self.slurm_scripts_path
        )
        
        # Block until it runs
        if job_id is not None and wait_for_job_start:
            is_running, time_waiting = self.wait_for_job(job_id, verbose=True)

            # Check for running and update metadata
            is_running = self.is_notebook_running(update_metadata=True)

            if is_running and start_tunnel:
                # Kill existing local ssh tunnels to job port
                self.kill_tunnels()
                
                # Start tunnel in background
                proc = subprocess.Popen(self.metadata["cmd"], shell=True,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          encoding="utf8")

                # Wait then check if process started
                sleep(1.0)
                if proc.poll() is None:
                    print("Started tunnel (port: %s, server: %s, pid: %d)" % (self.job_port, self.metadata["ip"], proc.pid))
                else:
                    logging.error("Failed to start tunnel with cmd: %s" % self.metadata["cmd"])
                
        
        # Get job ID from output and return
        return job_id
    
    def stop_notebook(self):
        """ Stops a notebook job if it is running. """
        
        if self.is_notebook_running():
            print("Stopping existing notebook (port %s, job id: %s)..." % (self.job_port, self.metadata["job_id"]))
            self.cancel_job(self.metadata["job_id"])
        else:
            print("No notebook running on port %s." % self.job_port)
            
    def find_tunnels(self):
        """ Finds ssh tunnels to specified job port and returns their process ids. """
        
        # Find ssh processes
        ssh_proc_info = [p.info for p in psutil.process_iter(attrs=["pid", "name", "cmdline"]) if isinstance(p.info["name"], str) and "ssh" in p.info["name"]]

        # Filter PIDs by ssh loopback arg to our job port
        pids = []
        for p in ssh_proc_info:
            if p["cmdline"] is not None and ("-L " + self.job_port) in " ".join(p["cmdline"]):
                pids.append(p["pid"])
        
        return pids
    
    def kill_tunnels(self):
        """ Kills any existing SSH tunnels to the specified port. """
        # Find tunnels
        pids = self.find_tunnels()
        
        # Kill each tunnel process
        for pid in pids:
            proc = psutil.Process(pid=pid)
            proc.kill()
            print("Killed ssh tunnel (port: %s, pid: %d)." % (self.job_port, pid))
            
    
