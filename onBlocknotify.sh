#!/bin/bash
ROOTDIR=<root directory>
F=${ROOTDIR}/block_log
D=`date +"%Y%m%d%H%M%S"`
echo BLK ${D} - $@ >> ${F}
cd ${ROOTDIR} && python ${ROOTDIR}/getdistribution.py $@ >> ${F}
