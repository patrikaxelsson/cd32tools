#!/usr/bin/env python

import sys
import os

if len(sys.argv) == 5:
	sourceDir = sys.argv[1]
	sourceDirAmigaPath = sys.argv[2]
	cdName = sys.argv[3]
	isoFileAmigaPath = sys.argv[4]
else:
	raise SystemExit("Usage: " + sys.argv[0].split('/')[-1] + " sourceDir sourceDirAmigaPath cdName isoFileAmigaPath")


print "0 0 3 0"
print "2 0"
print "8 16 40 16 32"
print "0 1 1 0"
print cdName
print
print
print
print

print isoFileAmigaPath
numDirectories = 1
for rootPath, dirNames, fileNames in os.walk(sourceDir):
	if rootPath == sourceDir:
		continue
	numDirectories = numDirectories + 1
print "{:04d}".format(numDirectories) + "\t" + sourceDirAmigaPath
print " 0001\t<Root Dir>"
dirNum = 1
for rootPath, dirNames, fileNames in os.walk(sourceDir):
	for dirName in dirNames:
		print " " + "{:04d}".format(dirNum) + "\t" + dirName
	dirNum = dirNum + 1
print

print "H0000\t<ISO Header>"
print "P0000\t<Path Table>"
print "P0000\t<Path Table>"
print "C0000\t<Trademark>"
dirNum = 1
for rootPath, dirNames, fileNames in os.walk(sourceDir):
	if rootPath == sourceDir:
		dirName = "<Root Dir>"
	else:
		dirName = rootPath.split('/')[-1]
	print "D" + "{:04d}".format(dirNum) + "\t" + dirName
	for fileName in fileNames:
		print "F" + "{:04d}".format(dirNum) + "\t" + fileName
	dirNum = dirNum + 1
print "E0000\t65536    "
