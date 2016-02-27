#!/usr/bin/env python

import sys
import struct

if len(sys.argv) == 3 and sys.argv[1] in ("print", "uppercase"):
	operation = sys.argv[1]

	isoFile = file(sys.argv[2], "rb")
	if "uppercase" == operation:
		isoFile = file(sys.argv[2], "rb+")
else:
	raise SystemExit("Usage: " + sys.argv[0].split('/')[-1] + " operation (print/uppercase) isoFile")

sectorSize = 2048

isoFile.seek(sectorSize * 0x10)

class PrimaryVolumeDescriptor:
	def __init__(self, volumeDescriptorData):
		self.logicalBlockSize, self.pathTableSize, self.pathTableLocMSB = struct.unpack(">2xH4xI8xI", volumeDescriptorData[128:128 + 4 + 8 + 8 + 4])
		self.pathTableLocLSB = struct.unpack("<I", volumeDescriptorData[140:140+ 4])[0]

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
		nameLen, self.extAttribLen, self.extAttribLoc, self.parentNum = struct.unpack(self.getHeaderStruct(), entryDataStart[:self.headerLength])
		self.name = entryDataStart[self.headerLength:self.headerLength + nameLen]
	
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
		data = struct.pack(completeStruct, nameLen, self.extAttribLen, self.extAttribLoc, self.parentNum, self.name)
		return data

	def getParents(self):
		parents = []
		currParent = self.parent
		while not currParent.isRoot():
			parents.append(currParent)
			currParent = currParent.parent
	
		parents.reverse()
		return parents

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


	def createChildren(self):
		for entry in self.entries:
			entry.children = []
			for potentialChild in self.getNonRootEntries():
				if entry == potentialChild.parent:
					entry.children.append(potentialChild)

	def updateParentNumsAndPositions(self):
		currentPos = 0
		for entry in self.entries:
			entry.parentNum = self.getEntryNum(entry.parent)
			entry.position = currentPos
			currentPos = currentPos + entry.getSize()
			
	def getEntryNum(self, entry):
		return self.entries.index(entry) + 1

	def getRootEntry(self):
		return self.entries[0]
	
	def getNonRootEntries(self):
		return self.entries[1:]

	def getAllChildren(self, entry):
		children = []
		for child in entry.children:
			children = children + [child] + self.getAllChildren(child)
		return children

	def sortEntriesDepthFirst(self):
		# Only need children lists for this operation
		self.createChildren()
		rootEntry = self.getRootEntry()
		self.entries = [rootEntry] + self.getAllChildren(self.getRootEntry())
		self.updateParentNumsAndPositions()

	def getEntriesAsData(self):
		data = ""
		for entry in self.entries:
			data = data + entry.getAsData()
		return data
			
	def printEntries(self):
		for entry in self.entries:
			pathElements = [e.name for e in entry.getParents() + [entry]]
			print entry.getRangeString() + "(" + str(len(pathElements)) + "): " + '/'.join(pathElements)
	
	def upperCaseEntries(self):
		for entry in self.entries:
			entry.name = entry.name.upper()


descriptor = getPrimaryVolumeDescriptor(isoFile)
print "PathTable size:", descriptor.pathTableSize


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
	isoFile.seek(descriptor.pathTableLocMSB * descriptor.logicalBlockSize)
	isoFile.write(pathTableMSB.getEntriesAsData())
	print "Uppercased MSB path table!"

	pathTableLSB.upperCaseEntries()
	isoFile.seek(descriptor.pathTableLocLSB * descriptor.logicalBlockSize)
	isoFile.write(pathTableLSB.getEntriesAsData())
	print "Uppercased LSB path table!"

isoFile.close()

if "print" == operation:
	pathTableMSB.printEntries()

