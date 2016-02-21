#!/usr/bin/env python

import sys
import os
from collections import deque

if len(sys.argv) == 5:
	sourceDir = sys.argv[1]
	sourceDirAmigaPath = sys.argv[2]
	cdName = sys.argv[3]
	isoFileAmigaPath = sys.argv[4]
else:
	raise SystemExit("Usage: " + sys.argv[0].split('/')[-1] + " sourceDir sourceDirAmigaPath cdName isoFileAmigaPath")


class PathNode:
	def __init__(self, path, parent):
		self.path = path
		self.name = os.path.split(path)[1]
		self.isDir = os.path.isdir(path)
		self.parent = parent
		self.children = None

	def getName(self):
		if self.parent == self:
			return "<Root Dir>"
		else:
			return self.name

	def getChildren(self):
		# Cache this so we just traverse the file system the first time
		if not self.children:
			self.children = [PathNode(os.path.join(self.path, childPath), self) for childPath in sorted(os.listdir(self.path), key=lambda s: s.upper())]
		return self.children

	def getPath(self):
		if self == self.parent:
			return self.name
		else:
			return os.path.join(self.parent.getPath(), self.name)

def breadthFirstWalker(rootNode):
	queue = deque()
	queue.appendleft(rootNode)
	while 0 != len(queue):
		node = queue.pop()
		if node.isDir:
			queue.extendleft(node.getChildren())
		yield node


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

print isoFileAmigaPath
rootNode = PathNode(sourceDir, None)
rootNode.parent = rootNode

dirNum = 0
for node in breadthFirstWalker(rootNode):
	if node.isDir:
		dirNum += 1
		node.num = dirNum

print "{:04d}".format(dirNum) + "\t" + sourceDirAmigaPath
for node in breadthFirstWalker(rootNode):
	if node.isDir:
		print " {:04d}".format(node.parent.num) + "\t" + node.getName()
print

print "H0000\t<ISO Header>"
print "P0000\t<Path Table>"
print "P0000\t<Path Table>"
print "C0000\t<Trademark>"
for node in breadthFirstWalker(rootNode):
	if node.isDir:
		print "D{:04d}".format(node.num) + "\t" + node.getName()
	else:
		print "F{:04d}".format(node.parent.num) + "\t" + node.getName()
print "E0000\t65536    "
