#!/bin/bash

case=$1
sample=$2
filetype=$3
template=$4

PROJECT=
PROJ_BASE=
WF_GEN=
DATE=$(date +%Y%m%d)
DATASET_IMPORT=
CONFIG="${sample}_$(basename -s '.template.config' $template).config"

# Activate environment
export GALAXY_API_KEY=
source activate glxy_wf

# Find sample files
case_dir=$(find ${PROJ_BASE} -name $case -type d | grep -i -v 'Test')
sample_dir=$(find ${case_dir} -name $sample -type d)
echo "Searching ${sample_dir} for $sample files."
sample_files=( $(find ${sample_dir} -name "*.$filetype" -type f | sort) )

if [ ${#sample_files[@]} -eq 0 ]; then
    echo "No files found for ${sample}."
    exit 1
fi

# Rename files if appropriate and rsync to the galaxy dataset import directory
destfiles=""
for sf in ${sample_files[@]}; do
    dest="${DATASET_IMPORT}/raw_data/$(basename $sf)"
    if [ ! -f $dest ]; then
        echo "Syncing $sf to $dest."
        srun rsync -ivazO $sf $dest
        chmod go+rx $dest
    else
        echo "$dest already exists, skipping sync." 
    fi
    destfiles+=( "$dest" )
done

echo "${destfiles[@]}"


# Generate config file"
# To Do: Changing file type to support standard galaxy extensions. Future work could expand support data tyeps.
filetype="tiff"
if [ ! -f ${WF_GEN}/configs/$CONFIG ]; then
    echo "Generating config"
    # Need jq 1.6 or greater
    yq  -y '.sample.name=$sample | .sample.filetype=$filetype | .sample.files=($ARGS.positional)' --arg sample $sample --arg filetype $filetype --args ${destfiles[@]} < $template > ${WF_GEN}/configs/$CONFIG
fi

# Run  Workflow
echo "Collecting inputs and invoking workflow in Galaxy"
srun glxy_wf collect_inputs ${WF_GEN}/configs/$CONFIG

# move outputs to patient dir
#sbatch ${PROJ_BASE}/code/move_outputs.sbatch $WORKFLOW $PATIENT $sample
