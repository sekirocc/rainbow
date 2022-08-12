#!/bin/bash
set -e -x

package_name=rainbow

echo 'prepare...'
rpmbuild_dir=/root/rpmbuild
ln -s `pwd`/contrib $rpmbuild_dir

cd core
version=`python setup.py --version`
release=1
cd ../

spec=$package_name.spec
sed -i "2i\%define version ${version}\n%define release ${release}" contrib/SPECS/$spec

echo 'rpmbuild...'
cd core
python setup.py sdist
cp dist/$package_name-$version.tar.gz ../contrib/SOURCES
cd ../

yum-builddep -y contrib/SPECS/$spec
rpmbuild -ba contrib/SPECS/$spec --define "dist .el7"
