#!/bin/bash
#SBATCH --time=00:01:00
#SBATCH --output='test_job.log'
#SBATCH --job-name='test_job'


echo "$0 $1 $2"
echo "Ran $SLURM_JOB_NAME (job ID: $SLURM_JOB_ID) at $(date)."

sleep 15
echo "[$(date)] Exiting..."
