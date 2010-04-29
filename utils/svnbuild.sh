#!/bin/bash

if [ $# -eq 0 ]
then
    echo "$0 <progname>"
    exit
fi

function cleanup {
    for d in ${tempdir} "build" "dist"
    do
        if [[ -d ${d} ]]; then
            echo " -> deleting directory ${d}"
            rm -rf ${d}
        fi
    done
    for f in "warn${progname}.txt" "${specfile}"
    do
        if [ -f ${f} ]; then
            echo " -> deleting file ${f}"
            rm -f ${f}
        fi
    done
}


progname=$1 
specfile="${progname}.spec"

module=${progname}
if [[ "${progname}" == "falsecolor2" ]]; then
    module="wxfalsecolor"
fi
tempdir="${module}_temp"
echo "progname : ${progname}"
echo "module   : ${module}"
echo "tempdir  : ${tempdir}"

revision=`svn info http://pyrat.googlecode.com/svn/trunk | grep ^Revision | cut -d ' ' -f 2`

## remove old directories and files
cleanup

echo "checking out ${progname} (revision=${revision})"
svn co http://pyrat.googlecode.com/svn/trunk/${module} ${tempdir}

## replace "REV" in file with revision number
echo "sed -i '' s/REV/${revision}/ ./${tempdir}/${progname}.py"
sed -i '' s/REV/${revision}/  ./${tempdir}/${progname}.py

echo "python /drives/c/pyinstaller-1.4/Makespec.py --onefile --console --icon=${progname}.ico ${tempdir}/${progname}.py"
python C:/pyinstaller-1.4/Makespec.py --onefile --console --icon=${progname}.ico ${tempdir}/${progname}.py
echo "python /drives/c/pyinstaller-1.4/Build.py ${specfile}"
python C:/pyinstaller-1.4/Build.py ${specfile}

## save executable
mv dist/${progname}.exe  ./${progname}.exe
## remove old directories and files
cleanup


