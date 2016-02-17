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
print
print

directories = {}

class Directory:
	def __init__(self, path, fileNames):
		self.path = path
		pathParts = path.split("/")
		self.depth = len(pathParts)
		if pathParts[-1] != "":
			self.name = pathParts[-1]
		else:
			self.name = "<Root Dir>"
		self.fileNames = sorted(fileNames, key=lambda s: s.lower())
	
	def getParentPath(self):
		return self.path.rsplit("/", 1)[0]

	def getParent(self):
		return directories[self.getParentPath()]
	
	def __lt__(self, other):
		if self.depth < other.depth:
			return True
		elif self.depth == other.depth:
			return self.path.upper().split("/") < other.path.upper().split("/")
		else:
			return False
	
	def __repr__(self):
		return str(self.depth) + " " + self.name + "-->" + self.getParent().name
	

print isoFileAmigaPath
for rootPath, dirNames, fileNames in os.walk(sourceDir.rstrip("/")):
	path = rootPath.split(sourceDir)[-1]
	directories[path] = Directory(path, fileNames)

directoryList = directories.values()
directoryList.sort()
for i, directory in enumerate(directoryList):
	directory.num = i + 1

print "{:04d}".format(len(directoryList)) + "\t" + sourceDirAmigaPath
for directory in directoryList:
	parent = directory.getParent()
	print " {:04d}".format(parent.num) + "\t" + directory.name
print

print "H0000\t<ISO Header>"
print "P0000\t<Path Table>"
print "P0000\t<Path Table>"
print "C0000\t<Trademark>"
for directory in directoryList:
	print "D" + "{:04d}".format(directory.num) + "\t" + directory.name
	for fileName in directory.fileNames:
		print "F" + "{:04d}".format(directory.num) + "\t" + fileName
print "E0000\t65536    "
