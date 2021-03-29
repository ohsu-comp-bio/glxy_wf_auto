#!/bin/bash

# Command Line Arguments
case=$1
sample=$2
filetype=$3
template=$4
assay=$5
extra_pattern=$6

# Static/semi-static script parameters
PROJECT=
PROJ_BASE=
WF_GEN=
DATE=$(date +%Y%m%d)
DATASET_IMPORT=
CONFIG="${sample}_$(basename -s '.template.config' $template).config"

# Activate environment
ENV_PATH=
source activate $ENV_PATH
export GALAXY_API_KEY=

# Find sample files
echo "Locating sample directory for $sample"
case_dir=$(find ${PROJ_BASE} -name $case -type d | grep -i -v 'Test')
sample_dir=$(find ${case_dir} -name $sample -type d)
echo "Searching ${sample_dir} for $sample files."
sample_files=( $(find ${sample_dir} -name "*.$filetype" -type f | sort) )

if [ ${#sample_files[@]} -eq 0 ]; then
    echo "No files found for ${sample}."
    exit 1
fi

# Define parameters that change by sample
# Start by identifying lab
if [[ $sample_dir =~ CHIN ]]; then
    lab=CHIN
elif [[ $sample_dir =~ HMS ]]; then
    lab=HMS 
elif [[ $sample_dir =~ COUSSENS ]]; then
    echo Error - have no implemented support for COUSSENS lab data
    exit 1
    lab=COUSSENS
else
    echo Error - no lab identified for sample directory \n $sample_dir
    exit 1
fi
# Get the metadata files based on lab
if [ -z "$assay" ]; then
    assay=HMS_Immune_v1
    echo Using default assay: $assay
else
    echo Assay provided: $assay
fi

# Find the sample files
# Define sort_files
# Description: Given the lab, sort the files
# Invocation: sort_files ${file_arr[@]}
function sort_files {
    local paths=( `ls $@` )
    local base_tmp
    # Define sorting/filtering strategy based on lab
    if [[ $lab =~ CHIN ]]
    then
        local qc_removed=( )
        for file in ${paths[@]}; do
            base_tmp=`basename $file`
            if [ ${base_tmp[@]:2:1} = Q ]; then
                continue
            elif [ ${base_tmp[@]:3:1} = Q ]; then
                continue
            else
                echo Using file $file
                qc_removed[${#qc_removed[@]}]=$file
            fi
        done
        cat << EOF
$( echo ${qc_removed[@]} | tr " " "\n" | sed 's/\(.*\)\//\1\t/' | sort -V -k 2 | sed 's/\t/\//' )
EOF
    else 
        echo Error: Sorting strategy not defined 0>2
        exit 1
    fi 
}
# Define find_sorted_samples
# Description: Determine strategy and find files in sorted order for sample path
# Invocation: find_sorted_function path/to/sample_dir [glob_pattern]
function find_sorted_files {
    local path=$1
    local glob=$2

    # Determine strategy for finding samples
    # If Chin lab sample
    if [[ $path =~ CHIN ]]
    then
        local final_glob=CZI*/R*${glob}*.${filetype}
        sort_files CHIN ${path}/${final_glob}

    elif [[ $path =~ HMS ]]
    then 
        sample_files=$(find $path -name '*rcpnl')
        cat << EOF                                                               
$( echo ${sample_files[@]} | tr " " "\n" | sed 's/\(.*\)\//\1\t/' | sort -V -k 2 | uniq | sed 's/\t/\//' )
EOF

    elif [[ $path =~ COUSSENS ]]
    then 
        >&2 echo No strategy defined for COUSSENS lab
        exit 1
    elif [[ $path =~ KDL ]]
    then
        >&2 echo No strategy defined for KDL
        exit 1
    else
        >&2 echo Lab not recognized - $lab
        exit 1
    fi 
}
echo Finding files from $sample_dir
sample_files=( $(find_sorted_files ${sample_dir} ${extra_pattern}) )

# Find the CSV files
csv_root="$DATASET_IMPORT"/common_inputs
library_path="OMSAtlas/common_inputs/{workflow}"
markers_csv=${csv_root}/${assay}_markers.csv
markers_lib=${library_path}/${assay}_markers.csv
typemap_csv=${csv_root}/${assay}_typemap.csv
typemap_lib=${library_path}/${assay}_typemap.csv
typemap_markers_csv=${csv_root}/${assay}_typemap_markers.txt
typemap_markers_lib=${library_path}/${assay}_typemap_markers.txt
typemap_simple_csv=${csv_root}/${assay}_typemap_simple.csv
typemap_simple_lib=${library_path}/${assay}_typemap_simple.csv
typemap_markers_simple_csv=${csv_root}/${assay}_typemap_markers_simple.txt
typemap_markers_simple_lib=${library_path}/${assay}_typemap_markers_simple.txt
if [ ! -f $markers_csv ]; then
    echo Files including $markers_csv not present in $csv_root
    exit 1
fi

# Rename files if appropriate and rsync to the galaxy dataset import directory
destfiles=""
for sf in ${sample_files[@]}; do
    dest="${DATASET_IMPORT}/${lab}/${sample/BEMS/0000}/$(basename $sf)"
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
bems_sample=${sample/0000/BEMS}
if [ ! -f ${WF_GEN}/configs/$CONFIG ]; then
    echo "Generating config"
    # Need jq 1.6 or greater
    yq  -y '.sample.name=$sample 
            | .sample.filetype=$filetype 
            | .sample.files=($ARGS.positional) 
            | .common_input_files.MARKERS=$markers_csv 
            | .common_input_files.TYPEMAP=$typemap_csv 
            | .common_input_files.TYPE_MARKERS=$typemap_markers_csv 
            | .common_input_files.TYPEMAP_SIMPLE=$typemap_simple_csv 
            | .common_input_files.TYPEMAP_MARKERS_SIMPLE=$typemap_markers_simple_csv 
            | .common_inputs.MARKERS=$markers_lib 
            | .common_inputs.TYPEMAP=$typemap_lib 
            | .common_inputs.TYPE_MARKERS=$typemap_markers_lib 
            | .common_inputs.TYPEMAP_SIMPLE=$typemap_simple_lib 
            | .common_inputs.TYPEMAP_MARKERS_SIMPLE=$typemap_markers_simple_lib'\
            --arg sample $bems_sample\
            --arg filetype $filetype\
            --arg markers_csv $markers_csv\
            --arg typemap_csv $typemap_csv\
            --arg typemap_markers_csv $typemap_markers_csv\
            --arg typemap_simple_csv $typemap_simple_csv\
            --arg typemap_markers_simple_csv $typemap_markers_simple_csv\
            --arg markers_lib $markers_lib\
            --arg typemap_lib $typemap_lib\
            --arg typemap_markers_lib $typemap_markers_lib\
            --arg typemap_simple_lib $typemap_simple_lib\
            --arg typemap_markers_simple_lib $typemap_markers_simple_lib\
            --args ${destfiles[@]} < $template > ${WF_GEN}/configs/$CONFIG
fi

# Run  Workflow
echo "Collecting inputs and invoking workflow in Galaxy"
srun glxy_wf collect_inputs ${WF_GEN}/configs/$CONFIG
#python glxy_wf/collect_inputs.py ${WF_GEN}/configs/$CONFIG

# move outputs to patient dir
#sbatch ${PROJ_BASE}/code/move_outputs.sbatch $WORKFLOW $PATIENT $sample
