#!/bin/bash
#SBATCH --time=24:00:00
#SBATCH --mem=128000
#SBATCH -N 1
#SBATCH --cpus-per-task=12
#SBATCH --ntasks-per-node=1
#SBATCH --ntasks-per-socket=1
#SBATCH --gres=gpu:1
#SBATCH -o '/tigress/bccho/logs/jupyter_lab_gpu.out'
#SBATCH -e '/tigress/bccho/logs/jupyter_lab_gpu.err'
#SBATCH --job-name='jupyter_lab_gpu'

source activate interactive


XDG_RUNTIME_DIR="" # important so that jupyter starts temp dir with correct permissions

# Get network info for the node
ip=$(hostname -i)
port=${1:-9010}
# port=$(shuf -i9010-9020 -n1)
notebook_dir="/tigress/bccho/code"

# Save connection info
json_path="$(pwd)/jupyter_lab.$port.json"
timestamp="$(date)"
echo -e "
{
    \"ip\": \"$ip\",
    \"port\": \"$port\",
    \"cmd\": \"ssh -N -o \\\"ExitOnForwardFailure yes\\\" -L $port:$ip:$port bccho@$SLURM_SUBMIT_HOST\",
    \"notebook_dir\": \"$notebook_dir\",
    \"json_path\": \"$json_path\",
    \"submit_host\": \"$SLURM_SUBMIT_HOST\",
    \"job_id\": \"$SLURM_JOB_ID\",
    \"job_name\": \"$SLURM_JOB_NAME\",
    \"cpus_on_node\": \"$SLURM_CPUS_ON_NODE\",
    \"timestamp\": \"$timestamp\"
}
" > "$json_path"
cat "$json_path"

# Start Jupyter Lab
jupyter-lab --no-browser --ip=$ip --port=$port --notebook-dir=$notebook_dir
# jupyter-notebook --no-browser --ip=$ip --port=$port
