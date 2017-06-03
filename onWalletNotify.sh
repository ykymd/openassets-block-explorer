#!/bin/bash
ROOTDIR=<root directory>
F=${ROOTDIR}/block_log
D=`date +"%Y%m%d%H%M%S"`
echo WAL ${D} - $@ >> ${F}
