#!/usr/bin/env python

import sys
import os
import struct
from collections import deque

if len(sys.argv) == 3 and sys.argv[1] in ("print", "uppercase"):
	operation = sys.argv[1]

	isoFile = file(sys.argv[2], "rb")
	if "uppercase" == operation:
		isoFile = file(sys.argv[2], "rb+")
else:
	raise SystemExit("Usage: " + os.path.basename(sys.argv[0]) + " operation (print/uppercase) isoFile")

sectorSize = 2048

isoFile.seek(sectorSize * 0x10)

class DirectoryEntry:
	def __init__(self, isoFile, location = None, blockSize = None):
		if location and blockSize:
			isoFile.seek(location * blockSize)

		self.data = isoFile.read(1)
		self.recordLen = struct.unpack("B", self.data)[0] 
		self.extentLoc = 0
		self.extentDataLen = 0
		self.flags = 0
		self.fileId = ""
		self.parent = None
		self.children = []
		if self.recordLen > 0:
			headerLength = 33
			self.data += isoFile.read(self.recordLen - 1)
			self.extRecordLen, self.extentLoc, self.extentDataLen, self.timestamp, self.flags, self.unitFlags, self.gapSize, self.volSeqNum, self.fileIdLen = struct.unpack(">B4xI4xI7sBBB2xHB", self.data[1:headerLength])
			self.fileId = self.data[headerLength:headerLength + self.fileIdLen]
			
			if self.isDir() and location == self.extentLoc:
				self.populateDirExtentData(isoFile, blockSize)

	def populateDirExtentData(self, isoFile, blockSize):
		endPos = self.extentLoc * blockSize + self.extentDataLen
		self.parent = DirectoryEntry(isoFile)
		while isoFile.tell() < endPos:
			childDirEntry = DirectoryEntry(isoFile)
			if childDirEntry.isEmpty():
				spaceLeftInBlock = blockSize - (isoFile.tell() % blockSize)
				isoFile.seek(spaceLeftInBlock, 1)
			else:
				self.children.append(childDirEntry)

	def isEmpty(self):
		return 0 == self.recordLen

	def isDir(self):
		return bool(self.flags & 0x02)

	def getName(self):
		return self.fileId.rsplit(";", 1)[0]

	def getAsData(self):
		return self.data

	def sortChildrenUppercased(self):
		self.children.sort(key=lambda c: c.getName().upper())

	def writeToFile(self, isoFile, blockSize):
		isoFile.seek(self.extentLoc * blockSize)
		isoFile.write(self.getAsData())
		isoFile.write(self.parent.getAsData())

		for child in self.children:
			spaceLeftInBlock = blockSize - (isoFile.tell() % blockSize)
			if child.recordLen > spaceLeftInBlock:
				isoFile.write('\0' * spaceLeftInBlock)
			isoFile.write(child.getAsData())
			
		spaceLeftInBlock = blockSize - (isoFile.tell() % blockSize)
		isoFile.write('\0' * spaceLeftInBlock)

	def __repr__(self):
		return ",".join([self.getName(), str(self.recordLen), str(self.isDir()), str(self.extentLoc), str(self.extentDataLen)])


class PrimaryVolumeDescriptor:
	def __init__(self, volumeDescriptorData):
		self.logicalBlockSize, self.pathTableSize, self.pathTableLocMSB = struct.unpack(">2xH4xI8xI", volumeDescriptorData[128:128 + 4 + 8 + 8 + 4])
		self.pathTableLocLSB = struct.unpack("<I", volumeDescriptorData[140:140 + 4])[0]

def getPrimaryVolumeDescriptor(isoFile):
	terminatorCode = 255
	primaryVolumeDescriptorCode = 1
	while True:
		volumeDescriptorData = isoFile.read(sectorSize)
		volumeDescriptorCode = struct.unpack("B", volumeDescriptorData[0:1])[0]
	
		if volumeDescriptorCode == terminatorCode:
			return None
		elif volumeDescriptorCode == primaryVolumeDescriptorCode:
			return PrimaryVolumeDescriptor(volumeDescriptorData)


class PathTableEntry:
	def __init__(self, entryDataStart, littleEndian, position):
		self.littleEndian = littleEndian
		self.position = position
		self.headerLength = 8
		nameLen, self.extentLen, self.extentLoc, self.parentNum = struct.unpack(self.getHeaderStruct(), entryDataStart[:self.headerLength])
		self.name = entryDataStart[self.headerLength:self.headerLength + nameLen]
		self.children = []
	
	def __repr__(self):
		return self.name + "'," + ",".join((str(self.parentNum), str(self.position), str(self.getSize())))

	def getHeaderStruct(self):
		headerStruct = "BBIH"
		if self.littleEndian:
			return "<" + headerStruct
		else:
			return ">" + headerStruct

	def getSize(self):
		nameLen = len(self.name)
		return self.headerLength + nameLen + nameLen % 2

	def getRangeString(self):
		start = self.position
		end = start + self.getSize() - 1
		return "{0:05d}-{1:05d}".format(start, end)

	def isRoot(self):
		# The root will point to itself
		return self == self.parent

	def getAsData(self):
		nameLen = len(self.name)
		completeStruct = self.getHeaderStruct() + str(nameLen) + "s" + str(nameLen % 2) + "x"
		data = struct.pack(completeStruct, nameLen, self.extentLen, self.extentLoc, self.parentNum, self.name)
		return data

	def getParents(self):
		parents = []
		currParent = self.parent
		while not currParent.isRoot():
			parents.append(currParent)
			currParent = currParent.parent
	
		parents.reverse()
		return parents


def breadthFirstWalker(rootNode):
	queue = deque()
	queue.appendleft(rootNode)
	while 0 != len(queue):
		node = queue.pop()
		queue.extendleft(node.children)
		yield node

class PathTable:
	def __init__(self, pathTableData, littleEndian):
		self.littleEndian = littleEndian
		self.entries = []
		headerLength = 8
		currentPos = 0
		while currentPos < descriptor.pathTableSize:
			entry = PathTableEntry(pathTableData[currentPos:], self.littleEndian, currentPos)
			self.entries.append(entry)
			currentPos = currentPos + entry.getSize()

		# Setup real parent links, which will survive a list sort
		for entry in self.entries:
			entry.parent = self.entries[entry.parentNum - 1]
			if entry != entry.parent: # Avoid the root being its own child also, makes it harder to walk the graph :)
				entry.parent.children.append(entry)
		
	def getRootEntry(self):
		return self.entries[0]
	
	def getNonRootEntries(self):
		return self.entries[1:]

	def upperCaseEntries(self):
		for entry in self.entries:
			entry.name = entry.name.upper()

	def updateParentNums(self):
		for i, entry in enumerate(self.entries):
			for child in entry.children:
				child.parentNum = i + 1

	def sortEntries(self):
		for entry in self.entries:
			entry.children.sort(key=lambda e: e.name)

		self.entries = [e for e in breadthFirstWalker(self.getRootEntry())]

		self.updateParentNums()

	def getEntriesAsData(self):
		data = ""
		for entry in self.entries:
			data = data + entry.getAsData()
		return data
			
	def printEntries(self):
		for entry in self.entries:
			pathElements = [e.name for e in entry.getParents() + [entry]]
			print entry.getRangeString() + "(" + str(len(pathElements)) + "): " + '/'.join(pathElements)
	


descriptor = getPrimaryVolumeDescriptor(isoFile)
print "PathTable size:", descriptor.pathTableSize

def sortDirEntriesUppercased(pathTable, blockSize):
	for pathTableEntry in pathTable.entries:
		dirEntry = DirectoryEntry(isoFile, pathTableEntry.extentLoc, blockSize)
		dirEntry.sortChildrenUppercased()
		dirEntry.writeToFile(isoFile, blockSize)
	
# Big endian path table is what is used on the CD32
isoFile.seek(descriptor.pathTableLocMSB * descriptor.logicalBlockSize)
pathTableMSB = PathTable(isoFile.read(descriptor.pathTableSize), False)

# Also process the little endian path table for completeness sake
isoFile.seek(descriptor.pathTableLocLSB * descriptor.logicalBlockSize)
pathTableLSB = PathTable(isoFile.read(descriptor.pathTableSize), True)
	
# Test comparison
#isoFile.seek(descriptor.pathTableLocMSB * descriptor.logicalBlockSize)
#pathTableMSBData = isoFile.read(descriptor.pathTableSize)
#testDataMSB = pathTableMSB.getEntriesAsData()
#print "TestDataMSBLength:", len(testDataMSB)
#print "MatchMSB:", pathTableMSBData == testDataMSB

if "uppercase" == operation:
	pathTableMSB.upperCaseEntries()
	pathTableMSB.sortEntries()
	isoFile.seek(descriptor.pathTableLocMSB * descriptor.logicalBlockSize)
	isoFile.write(pathTableMSB.getEntriesAsData())
	print "Uppercased and resorted MSB path table!"

	pathTableLSB.upperCaseEntries()
	pathTableLSB.sortEntries()
	isoFile.seek(descriptor.pathTableLocLSB * descriptor.logicalBlockSize)
	isoFile.write(pathTableLSB.getEntriesAsData())
	print "Uppercased and resorted LSB path table!"
	
	sortDirEntriesUppercased(pathTableMSB, descriptor.logicalBlockSize)
	print "Sorted directory entries in uppercased name order!"

isoFile.close()

if "print" == operation:
	pathTableMSB.printEntries()

