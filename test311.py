import random
import unittest
import urllib
import types
import re
from xml.dom import minidom

SERVICE_ELEMENT_NAMES = ('service_code', 'metadata', 'type', 'keywords', 'group', 'service_name', 'description')
ATTRIBUTE_ELEMENT_NAMES = ('variable', 'code', 'datatype', 'required', 'datatype_description', 'order', 'description', 'description')
SERVICE_REQUEST_ELEMENT_NAMES = ('service_request_id', 'status', 'status_notes', 'service_name', 'service_code', 'description', 'agency_responsible', 'service_notice', 'requested_datetime', 'updated_datetime', 'expected_datetime', 'address', 'address_id', 'zipcode', 'lat', 'long', 'georss:point')
JURISDICTION_ID = 'dc.gov'
#URL_OPEN_311 = 'http://311.test.in.dc.gov/csr/Open311'
URL_OPEN_311 = 'http://311.dc.gov/csr/Open311'
API_KEY = '7d7859704a'
#JURISDICTION_ID = 'sfgov.org'
#URL_OPEN_311 = 'https://open311.sfgov.org/dev/V2'
#API_KEY = 'DT'

def parseServices(dom):
	services = []
	for serviceEl in dom.getElementsByTagName('service'):
		services.append(parseService(serviceEl))
	return services
		
def parseService(serviceEl):
	service = {}
	for elName in SERVICE_ELEMENT_NAMES:
		print elName
		service[elName] = serviceEl.getElementsByTagName(elName)[0].childNodes[0].data
	return service

def parseServiceDefinition(dom):
	sd = {}
	sdEl = dom.getElementsByTagName('service_definition')[0]
	sd['service_code'] = sdEl.getElementsByTagName('service_code')[0].childNodes[0].data
	sd['attributes'] = []
	for attrEl in sdEl.getElementsByTagName('attribute'):
		attribute = {}
		for attrElName in ATTRIBUTE_ELEMENT_NAMES:
			attribute[attrElName] = \
			 attrEl.getElementsByTagName(attrElName)[0].childNodes[0].data
		values = {}
		for valEl in attrEl.getElementsByTagName('value'):
			values[valEl.getElementsByTagName('key')[0].childNodes[0].data] = \
				valEl.getElementsByTagName('name')[0].childNodes[0].data
		attribute['values'] = values
		sd['attributes'].append(attribute)
	return sd

def parseServiceRequests(dom):
	srs = []
	for srEl in dom.getElementsByTagName('request'):
		srs.append(parseServiceRequest(srEl))
	return srs

def parseServiceRequest(srEl):
	sr = {}
	for elName in SERVICE_REQUEST_ELEMENT_NAMES:
		els = srEl.getElementsByTagName(elName)
		if len(els):
			nodes = els[0].childNodes
			if len(nodes):
				sr[elName] = nodes[0].data
	return sr

def parseSubmitResult(dom):
	result = {}
	return result
	
def getServices(opener):
	url = "%s/services.xml?%s" % (URL_OPEN_311, urllib.urlencode({'jurisdiction_id':JURISDICTION_ID}))
	dom = minidom.parse(opener.open(url))
	f = open('services.xml', 'w')
	f.write(dom.toxml())
	f.close()
	return parseServices(dom)

def getServiceDefinition(opener, serviceCode):
	url = "%s/service_definition.xml?%s" % (URL_OPEN_311, urllib.urlencode({'jurisdiction_id':JURISDICTION_ID, 'service_code':serviceCode}))
	dom = minidom.parse(opener.open(url))
	f = open('service_definition_%s.xml' % serviceCode, 'w')
	f.write(dom.toxml())
	f.close()
	return parseServiceDefinition(dom)

def getServiceRequests(opener, serviceCode):
	url = "%s/requests.xml?%s" % (URL_OPEN_311, urllib.urlencode({'jurisdiction_id':JURISDICTION_ID, 'service_code':serviceCode}))
	dom = minidom.parse(opener.open(url))
	f = open('requests_%s.xml' % serviceCode, 'w')
	f.write(dom.toxml())
	f.close()
	return parseServiceRequests(dom)

def submitServiceRequest(opener, serviceRequestDict):
	serviceRequestDict.update({'jurisdiction_id':JURISDICTION_ID, 'api_key':API_KEY})
	url = "%s/requests.xml" % (URL_OPEN_311)
	data = opener.open(url, urllib.urlencode(serviceRequestDict))
	dom = minidom.parse(data)
	print 'CODE: %s' % data.getcode()
	f = open('requests_submit.xml', 'w')
	f.write(dom.toxml())
	f.close()
	return parseSubmitResult(dom)

class TestOpen311(unittest.TestCase):
	
	def setUp(self):
		self.opener = urllib.FancyURLopener({})
		
	def testServices(self):
		for s in getServices(self.opener):
			self.assertTrue(re.search('.+', s.get('service_code', '')), 'service_code is required')
			self.assertTrue(s['metadata'] in ('true', 'false'), 'metadata must be a boolean string')
			self.assertTrue(s['type'] in ('realtime', 'batch', 'blackbox'), 'type is not a valid type')
			self.assertTrue(re.search('.+', s.get('description', '')), 'description is required')
			
	def testServiceDefinitions(self):
		for s in getServices(self.opener):
			if s['metadata'] == 'true' or s['metadata'] == 'True' or s['metadata'] is True:
				sd = getServiceDefinition(self.opener, s['service_code'])
				print 'Found service definition for service code: %s' % s['service_code']
				self.assertEqual(sd['service_code'], s['service_code'], 'Service codes did not match.')
				for attr in sd['attributes']:
					self.assertTrue(attr['variable'] in ('true', 'false'), 'variable must be a boolean string')
					self.assertTrue(re.search('.+', attr.get('code', '')), 'code is required')
					self.assertTrue(attr['datatype'] in ('string', 'number', 'datetime', 'text', 'singlevaluelist', 'multivaluelist'), 'datatype is not a valid type')
					self.assertTrue(attr['required'] in ('true', 'false'), 'required must be a boolean string')
					self.assertTrue(type(eval(attr['order'])) in (types.IntType, types.FloatType), 'order = %s is not valid' % attr['order'])
					
	def testServiceRequests(self):
		for s in getServices(self.opener):
			srs = getServiceRequests(self.opener, s['service_code'])
			print 'Found %s service requests for service code: %s' % (len(srs), s['service_code'])
			for sr in srs:
				print '\tFound service request id: %s' % sr['service_request_id']
				self._testServiceRequest(sr)
				
	def _testServiceRequest(self, sr):
		print sr
		self.assertTrue(re.search('.+', sr.get('service_request_id', '')), 'service_request_id is required')
		self.assertTrue(sr['status'] in ('open', 'closed'), 'status is not a valid type')
		if sr.get('service_name', False):
			self.assertTrue(re.search('.+', sr.get('service_name', '')), 'service_name is required %s' % sr)
		if sr.get('service_code', False):
			self.assertTrue(re.search('.+', sr.get('service_code', '')), 'service_code is required')
		self.assertTrue(re.search('^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z?$', sr['requested_datetime']), 'requested_datetime is not a valid datetime')
		if sr.get('updated_datetime', False):
			self.assertTrue(re.search('^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z?$', sr['updated_datetime']), 'updated_datetime is not a valid datetime')
		if sr.get('expected_datetime', False):
			self.assertTrue(re.search('^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z?$', sr['expected_datetime']), 'expected_datetime is not a valid datetime')
		self.assertTrue(re.search('.+', sr['address']), 'address is required')
		if sr.get('zipcode', False):
			self.assertEqual(type(eval(sr['zipcode'])), types.IntegerType, 'zipcode is not valid')
		if sr.get('lat', False):
			self.assertEqual(type(eval(sr['lat'])), types.FloatType, 'lat is not valid')
		if sr.get('long', False):
			self.assertEqual(type(eval(sr['long'])), types.FloatType, 'long is not valid')
		if sr.get('georss:point', False):
			lat, lon = sr['georss:point'].split(' ')
			self.assertEqual(type(eval(lat)), types.FloatType, 'georss:point lat is not valid')
			self.assertEqual(type(eval(lon)), types.FloatType, 'georss:point lon is not valid')
	
	def testSubmitServiceRequest(self):
		print submitServiceRequest(self.opener, {'service_code':'DMV66'}).read()
		
if __name__ == '__main__':
	suite = unittest.TestLoader().loadTestsFromTestCase(TestOpen311)
	unittest.TextTestRunner(verbosity=2).run(suite)