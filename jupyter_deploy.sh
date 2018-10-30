#!/bin/bash


VDIR=venv2.7
VIRT_CREATE=/usr/apps/python/bin/virtualenv

if [ ! -f $VIRT_CREATE ]; then
	echo "virtualenv does not exist: "$VIRT_CREATE
	return 1;
fi


#  make sure that the user does not have a virtual environment currently active
#  because removing an activated virtual environment could cause problems
deactivate

#   if any command fails, the script will fail with an error code
set -e

rm -rf $VDIR
 
#  Create a virtual environment
$VIRT_CREATE --system-site-package $VDIR
 
#  Start virtual env.
source $VDIR/bin/activate

if [ ! -d sina ]; then
	git clone ssh://git@cz-bitbucket.llnl.gov:7999/sibo/sina.git
fi

cd sina
pip install  -r requirements.txt

pip install --upgrade pip
 
python -m pip install ipykernel
 
#  Create a kernel
python -m ipykernel install --prefix=$HOME/.local/ --name $VDIR --display-name $VDIR

echo ''
echo ''
echo ''
echo '-------------------------------------------------------------------------------'
echo 'pip install xxxx'
echo '-------------------------------------------------------------------------------'
 
#  These widgets give you sliders, drop downs, input fields, date pickers, etc
pip install ipywidgets
 
#  For creating charts and plots with hover overs, etc.
pip install plotly
 
#  Needed for running Sina
pip install sqlalchemy
 
#  Needed  for running example code, to output in a table
pip install tabulate



