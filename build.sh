#! /bin/bash

# Set minimum required versions
PYTHON_MINIMUM_MAJOR=3
PYTHON_MINIMUM_MINOR=3

# Get python references
PYTHON3_REF=$(which python3 | grep "/python3")
PYTHON_REF=$(which python | grep "/python")

error_msg(){
    echo "Python executable not found"
}

python_ref(){
    local my_ref=$1
    echo $($my_ref -c 'import platform; major, minor, patch = platform.python_version_tuple(); print(major); print(minor);')
}

# Print success_msg/error_msg according to the provided minimum required versions
check_version(){
    local major=$1
    local minor=$2
    local python_ref=$3
    [[ $major -ge $PYTHON_MINIMUM_MAJOR && $minor -ge $PYTHON_MINIMUM_MINOR ]] && echo $python_ref || error_msg
}

# Logic
if [[ ! -z $PYTHON3_REF ]]; then
    version=($(python_ref python3))
    check_version ${version[0]} ${version[1]} $PYTHON3_REF
    PYTHON_EXEC=python3
elif [[ ! -z $PYTHON_REF ]]; then
    # Didn't find python3, let's try python
    version=($(python_ref python))
    check_version ${version[0]} ${version[1]} $PYTHON_REF
    PYTHON_EXEC=python
else
    # Python is not installed at all
    error_msg
fi


VIRTUAL_ENV_ACTIVE=$($PYTHON_EXEC -c "import sys; print(hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))")

if [ $VIRTUAL_ENV_ACTIVE = "False" ]; then
    if [ ! -d "./venv/bin" ]; then
        $PYTHON_EXEC -m "venv" ./venv
    fi
    source "./venv/bin/activate"
    pip install -r requirements.txt
    STARTED_VENV=0
fi

pyinstaller \
	--add-data "Plugins:Plugins" \
	--additional-hooks-dir "hooks" \
	"$@" smarthash.py

if [ $STARTED_VENV ]; then
    deactivate
fi
