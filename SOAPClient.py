from zeep import Client
from zeep.transports import Transport
import constants
import time
import sys

class SOAPClient:
	def __init__(self, url):
		transport = Transport(timeout = 120, operation_timeout = 300)
		self.cl = Client(wsdl = url, transport = transport)
		self.loginToken = ''
		self.uploadToken = ''

	def login(self, user, passwd):
		if (constants.dryrun): return('fakeToken')
		self.loginToken = self.cl.service.Login(user, passwd)
		return(self.loginToken)
	def loginM(self, loginToken):
		self.loginToken = loginToken
	def logout(self):
		if (constants.dryrun): return
		if (self.loginToken == ''): return
		self.cl.service.Logout(self.loginToken)
		self.loginToken = ''

	def getLoadStatus(self, spaceId):
		if (constants.dryrun): return('Available')
		return(self.cl.service.getLoadStatus(self.loginToken, spaceId))

	def beginDataUpload(self, spaceId, sourceName):
		if (constants.dryrun):
			#raise NameError('beginDataUpload fail')
			return('fakeToken')
		self.uploadToken = self.cl.service.beginDataUpload(self.loginToken, spaceId, sourceName)
		return(self.uploadToken)

	def setDataUploadOptions(self, uploadToken, options):
		if (constants.dryrun): return
		ArrayOfString = self.cl.get_type('ns0:ArrayOfString')
		self.cl.service.setDataUploadOptions(self.loginToken, uploadToken, ArrayOfString(options))

	def uploadData(self, uploadToken, numBytes, binaryData):
		if (constants.dryrun):
			#raise NameError('uploadData fail')
			return
		self.cl.service.uploadData(self.loginToken, uploadToken, numBytes, binaryData)

	def finishDataUpload(self, uploadToken):
		if (constants.dryrun):
			#raise NameError('finishDataUpload fail')
			return
		self.cl.service.finishDataUpload(self.loginToken, uploadToken)
		self.uploadToken = ''
	def cancelDataUpload(self, loginToken, uploadToken):
		if (constants.dryrun or uploadToken == ''): return
		self.cl.service.finishDataUpload(loginToken, uploadToken)

	def isJobComplete(self, uploadToken):
		if (constants.dryrun):
			#raise NameError('isJobComplete fail')
			return(True)
		return(self.cl.service.isJobComplete(self.loginToken, uploadToken))

	def getJobStatus(self, jobToken):
		if (constants.dryrun):
			#raise NameError('getJobStatus fail')
			status = fakeStatusObj()
			return(status)
		return(self.cl.service.getJobStatus(self.loginToken, jobToken))

	def publishData(self, spaceId, groups, date):
		if (constants.dryrun): return('fakeToken')
		ArrayOfString = self.cl.get_type('ns0:ArrayOfString')
		return(self.cl.service.publishData(self.loginToken, spaceId, ArrayOfString(groups), date))

	def swapSpaceContents(self, spaceId1, spaceId2):
		if (constants.dryrun): return('fakeToken')
		return(self.cl.service.swapSpaceContents(self.loginToken, spaceId1, spaceId2))

	def copySpaceContents(self, spaceIdFrom, spaceIdTo):
		if (constants.dryrun): return('fakeToken')
		return(self.cl.service.copySpaceContents(self.loginToken, spaceIdFrom, spaceIdTo))

class fakeStatusObj(object):
	def __init__(self):
		#self.statusCode = 'Failed'
		#self.message = 'Dry run failed msg'
		self.statusCode = 'Dry run status code'
		self.message = 'Dry run ok msg'
