import os
import sys
import glob
import time
import csv
import argparse
from datetime import datetime
import subprocess

#configuration region:

bootloaderFilename 		= 'xenon-bootloader@1.4.4.bin'
systemPart1Filename 	= 'xenon-system-part1@1.4.4.bin'
mainApplicationFilename = 'xenon-tinker@1.4.4.bin'
softDeviceFirmware = 'xenon-softdevice@1.4.4.bin'
configDoneFirmware = 'dummy.bin'


# bootloaderFilename 		= 'boron-bootloader@1.4.0-rc.1.bin'
# systemPart1Filename 	= 'boron-system-part1@1.4.0-rc.1.bin'
# mainApplicationFilename = 'boron-tinker@1.4.0-rchit.1.bin'
# boronSoftDeviceFirmware = 'boron-softdevice@1.4.0-rc.1.bin'
# boronConfigDoneFirmware = 'dummy.bin'

#argon
#dfuDeviceID = "2b04:d00c"

#boron
dfuDeviceID = "2b04:d00d"

#xenon
dfuDeviceID = "2b04:d00e"

#argon
#systemPart1Address = '0x00030000'
#userAppAddress = '0x000D4000'

#boron
# systemPart1Address = '0x00030000'
# userAppAddress = '0x000D4000'
# configDoneAddress = '8134'

#xenon
systemPart1Address = '0x00030000'
userAppAddress = '0x000D4000'
configDoneAddress = '8134'


serialPortPrefix = "/dev/"
isWindows = False




## photon
# systemPart1Filename = 'system-part1-1.0.1-photon.bin'
# systemPart2Filename = 'system-part2-1.0.1-photon.bin'
# mainApplicationFilename = 'firmware.bin'
# serialPortPrefix = "/dev/"
# dfuDeviceID = "2b04:d006
# isWindows = False




def getBaudCommand(p, baud):
	if isWindows:
		return "MODE " + p + ":baud=" + baud + "\n"
	else:
		return "stty -f " + p + " " + baud + "& "


def log_device_id():
	print('logging device id')
	command = ('particle identify')
	p = subprocess.Popen(command, universal_newlines=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	text = p.stdout.read()
	retcode = p.wait()

	# append text to a file
	f=open("devices.txt", "a+")
	f.write(text)
	f.close()

	return 0

def inspect():
	print('attempting to inspect device modules via serial')

	p = ports()
	if p == None:
		print("No ready serial ports detected... waiting a few seconds and trying again")
		time.sleep(5)

	p = ports()
	if p == None:
		print("No ready serial ports detected... waiting a few seconds and trying again")
		time.sleep(5)

	command = ('particle serial inspect')
	p = subprocess.Popen(command, universal_newlines=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	text = p.stdout.read()
	retcode = p.wait()

	flag1 = "Bootloader module #0 - version 501," in text
	flag2 = "System module #1 - version 1406," in text
	flag3 = "UUID: 78E75D425AC3616DA4A943D5B2A361C01652F77B796F5C15313B0C806224A274" in text

	allTrue = flag1 and flag2 and flag3
	return allTrue


def ports():
	try:
		print('looking for active serial ports')
		command = ('particle serial list')
		p = subprocess.Popen(command, universal_newlines=True,
							 shell=True, stdout=subprocess.PIPE,
							 stderr=subprocess.PIPE)

		text = p.stdout.read()
		retcode = p.wait()

		searchlines = text.splitlines()

		for line in searchlines:
			if serialPortPrefix in line:
				#'/dev/tty.usbmodem1411 - Photon'

				if isWindows:
					# not ideal, split would be safer
					return line[:5].rstrip(" ")
				else:
					#TODO: testing on windows?
					parts = line.split(' - ')
					return parts[0]

		return None
	except:
		print("Unexpected error in ports:", sys.exc_info()[0])
		return None


def checkDFUMode():
	command = ('dfu-util --list')
	p = subprocess.Popen(command, universal_newlines=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	text = p.stdout.read()
	retcode = p.wait()

	# command output looks like this:
	# Found Runtime: [05ac:8289] ver=0118, devnum=7, cfg=1, intf=3, alt=0, name="UNKNOWN", serial="UNKNOWN"
	# Found DFU: [2b04:d006] ver=0250, devnum=25, cfg=1, intf=0, alt=1, name="@DCT Flash   /0x00000000/01*016Kg", serial="3a0036000247363333343435"
	# Found DFU: [2b04:d006] ver=0250, devnum=25, cfg=1, intf=0, alt=0, name="@Internal Flash   /0x08000000/03*016Ka,01*016Kg,01*064Kg,07*128Kg", serial="3a0036000247363333343435"

	testString = 'Found DFU: [' + dfuDeviceID + ']'
	return testString in text


#
#---------------------------------

def requestDFUMode():
	try:
		print('attempting to put device in DFU mode')

		# do we have any ports?
		p = ports()
		if p == None:
			print("No ready serial ports detected... waiting a few seconds and trying again")
			time.sleep(5)

		p = ports()
		if p == None:
			print("No ready serial ports detected... giving up")
			return False

		command = getBaudCommand(p, "14400")
		ret = subprocess.call(command, shell=True)
		if not isWindows:
			if ret is not 0:
				print 'failed to call flashsys.bat'
				return False
		else:
			print "unable to check return code on windows "

		time.sleep(2)
		if checkDFUMode():
			return True

		# hmm, otherwise, lets wait a little longer and see
		time.sleep(2)

		# TODO: do we want to try triggering the mode again?
		return checkDFUMode()
	except:
		print("Unexpected error in requestDFUMode:", sys.exc_info()[0])
		return None


#
#---------------------------------

def requestSETUPMode():
	print('attempting to put device in SETUP mode')

	# do we have any ports?
	p = ports()
	if p == None:
		print("No ready serial ports detected... waiting a few seconds and trying again")
		time.sleep(5)

	p = ports()
	if p == None:
		print("No ready serial ports detected... giving up")
		return False

	command = getBaudCommand(p, "28800")

	ret = subprocess.call(command, shell=True)
	if ret is not 0:
		print 'failed to call flashsetup.bat'
		return False

	time.sleep(2)

	#check to ensure device is in SETUP mode
	isInSetupMode = ports() is not None

	return isInSetupMode


def updateSystemFirmware():
	print('attempting to flash system firmware')

	if checkDFUMode() == False:
		if requestDFUMode() == False:
			print('Failed to put the device into DFU mode... bailing')
			sys.exit(1)

	#subprocess.call('particle flash --usb ' + systemPart1Filename, shell=True)
	subprocess.call('dfu-util -d '+dfuDeviceID+' -a 0 -s '+systemPart1Address+':leave -D ' + systemPart1Filename, shell=True)
	#subprocess.call('dfu-util -d '+dfuDeviceID+' -a 0 -s 0x8060000:leave -D ' + systemPart2Filename, shell=True)

	# wait for the device to restart or whatever it needs with the new firmware
	time.sleep(4)

def updateSoftdevice():
	print('attempting to put device in SETUP mode')
	if requestSETUPMode() == False:
		print('Failed to put the device into SETUP mode... bailing')
		sys.exit(1)

	isInSetupMode = ports() is not None
	if not isInSetupMode:
		print('Failed to put the device into SETUP mode... bailing')
		sys.exit(1)
		return False

	command = 'particle flash --serial --yes ' + softDeviceFirmware
	print('attempting to flash soft device update')
	subprocess.call(command, shell=True)
	time.sleep(5)


def updateBootloader():
	print('attempting to put device in SETUP mode')
	if requestSETUPMode() == False:
		print('Failed to put the device into SETUP mode... bailing')
		sys.exit(1)

	isInSetupMode = ports() is not None
	if not isInSetupMode:
		print('Failed to put the device into SETUP mode... bailing')
		sys.exit(1)
		return False

	command = 'particle flash --serial --yes ' + bootloaderFilename
	print('attempting to flash bootloader')
	subprocess.call(command, shell=True)
	time.sleep(5)


def updateMainFirmware():
	print('attempting to flash application firmware')

	if checkDFUMode() == False:
		if requestDFUMode() == False:
			print('Failed to put the device into DFU mode... bailing')
			sys.exit(2)

	subprocess.call('dfu-util -d '+dfuDeviceID+' -a 0 -s '+userAppAddress+':leave -D ' + mainApplicationFilename, shell=True)
	time.sleep(2)


def setConfigDoneBit():
	print('attempting to set the config done bit')

	if checkDFUMode() == False:
		if requestDFUMode() == False:
			print('Failed to put the device into DFU mode... bailing')
			sys.exit(2)

	subprocess.call('dfu-util -d '+dfuDeviceID+' -a 1 -s '+configDoneAddress+':leave -D ' + configDoneFirmware,
					shell=True)
	time.sleep(2)



def determineSuccess():
	print('checking if updates were successful')
	result = inspect()

	if result:
		print("PASS")
		return 0
	else:
		print("FAIL")
		return 3


startTime = time.time()


#
# Flash System Firmware
#
updateSystemFirmware()



#
#	Flash Bootloader
#
updateBootloader()

#
#	Update Softdevice
#
updateSoftdevice()


#
#	Flash Main Application
#
updateMainFirmware()

#
#	Check module info to make sure we won't boot in safe mode
#
resultCode = determineSuccess()

log_device_id()

#
#	Set Done Bit
#
setConfigDoneBit()

if resultCode == 0:
    print("+")
    print("+")
    print("+")
    print("PASS")
    print("+")
    print("+")
    print("+")
else:
    print("x")
    print("x")
    print("x")
    print("FAIL")
    print("x")
    print("x")
    print("x")

endTime = time.time()
duration = str(endTime - startTime)
print "Device upgrade succeeded after " + duration + " seconds"

sys.exit(resultCode)


