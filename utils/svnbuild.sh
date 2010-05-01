#!/bin/bash


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

function usage {
    echo -e "\nUsage:\n\n    $0 [-v version] <progname>\n"
}

## parse arguments for version option
version=""
args=`getopt v: $*`
if [ $? != 0 ]
then
    usage
    exit 2
fi
set -- $args

for i
do
    case "$i"
    in
        -v)
            version=$2; shift;
            shift;;
        --)
            shift; break;;
    esac
done

## remaining argument is progname
progname=$1
if [[ $progname == "" ]]
then
    usage
    exit 2
fi

module=${progname}
if [[ "${progname}" == "falsecolor2" ]]; then
    module="wxfalsecolor"
fi

if [[ ${version} == "" ]]
then 
    repopath="http://pyrat.googlecode.com/svn/trunk/${module}"
else
    repopath="http://pyrat.googlecode.com/svn/tags/${module}/${version}"
fi
    
specfile="${progname}.spec"
tempdir="${module}_temp"

echo "progname : ${progname}"
echo "version  : ${version}"
echo "module   : ${module}"
echo "repopath : ${repopath}"
echo "tempdir  : ${tempdir}"

    
revision=`svn info ${repopath} | grep ^Last\ Changed\ Rev | cut -d ' ' -f 4`
#if [[ $? -ne 0 ]]
if [[ ${revision} == "" ]]
then 
    echo "error getting svn info for ${repopath}"
    exit 1
fi
echo "revision : ${revision}"


## remove old directories and files
cleanup

echo -e "\nchecking out ${progname} (revision=${revision})"
svn co ${repopath} ${tempdir}

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


