#!/usr/bin/env python
# coding=utf-8
'''
Created on 2017年6月14日

@author: JIAYUE
'''
# AWS Version 4 signing example

# EC2 API (DescribeRegions)

# See: http://docs.aws.amazon.com/general/latest/gr/sigv4_signing.html
# This version makes a GET request and passes the signature
# in the Authorization header.
import sys, os, base64, datetime, hashlib, hmac 
import requests # pip install requests
from urllib.parse import urlencode
import traceback
import json

class AwsRequest(object):
    '''
    __init__ method
    '''
    def __init__(self, service, host, region, endpoint, access_key, secret_key):
        self.method = 'GET'
        self.service = service
        self.host = host
        self.region = region
        self.endpoint = endpoint
        
        if access_key is None or secret_key is None:
            print('No access key is available.')
            sys.exit()
        self.access_key = access_key
        self.secret_key = secret_key
    
    @staticmethod
    def sign(key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    @staticmethod
    def getSignatureKey(key, dateStamp, regionName, serviceName):
        kDate = AwsRequest.sign(('AWS4' + key).encode('utf-8'), dateStamp)
        kRegion = AwsRequest.sign(kDate, regionName)
        kService = AwsRequest.sign(kRegion, serviceName)
        kSigning = AwsRequest.sign(kService, 'aws4_request')
        return kSigning
    
    def getHeaderse(self, request_parameters):
        # Create a date for headers and the credential string
        t = datetime.datetime.utcnow()
        amzdate = t.strftime('%Y%m%dT%H%M%SZ')
        datestamp = t.strftime('%Y%m%d') # Date w/o time, used in credential scope
        
        # ************* TASK 1: CREATE A CANONICAL REQUEST *************
        # http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html
        
        # Step 1 is to define the verb (GET, POST, etc.)--already done.
        
        # Step 2: Create canonical URI--the part of the URI from domain to query 
        # string (use '/' if no path)
        canonical_uri = '/' 
        
        # Step 3: Create the canonical query string. In this example (a GET request),
        # request parameters are in the query string. Query string values must
        # be URL-encoded (space=%20). The parameters must be sorted by name.
        # For this example, the query string is pre-formatted in the request_parameters variable.
        request_parameters = sorted(request_parameters.items(), key=lambda d: d[0])
        canonical_querystring = urlencode(request_parameters)
        
        # Step 4: Create the canonical headers and signed headers. Header names
        # must be trimmed and lowercase, and sorted in code point order from
        # low to high. Note that there is a trailing \n.
        canonical_headers = 'host:' + self.host + '\n' + 'x-amz-date:' + amzdate + '\n'
        
        # Step 5: Create the list of signed headers. This lists the headers
        # in the canonical_headers list, delimited with ";" and in alpha order.
        # Note: The request can include any headers; canonical_headers and
        # signed_headers lists those that you want to be included in the 
        # hash of the request. "Host" and "x-amz-date" are always required.
        signed_headers = 'host;x-amz-date'
        
        # Step 6: Create payload hash (hash of the request body content). For GET
        # requests, the payload is an empty string ("").
        payload_hash = hashlib.sha256(b'').hexdigest()
        
        # Step 7: Combine elements to create create canonical request
        canonical_request = self.method + '\n' + canonical_uri + '\n' + canonical_querystring + '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash
        
        # ************* TASK 2: CREATE THE STRING TO SIGN*************
        # Match the algorithm to the hashing algorithm you use, either SHA-1 or
        # SHA-256 (recommended)
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = datestamp + '/' + self.region + '/' + self.service + '/' + 'aws4_request'
        string_to_sign = algorithm + '\n' +  amzdate + '\n' +  credential_scope + '\n' +  hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()


        # ************* TASK 3: CALCULATE THE SIGNATURE *************
        # Create the signing key using the function defined above.
        signing_key = AwsRequest.getSignatureKey(self.secret_key, datestamp, self.region, self.service)
        
        # Sign the string_to_sign using the signing_key
        signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()


        # ************* TASK 4: ADD SIGNING INFORMATION TO THE REQUEST *************
        # The signing information can be either in a query string value or in 
        # a header named Authorization. This code shows how to use a header.
        # Create authorization header and add to request headers
        authorization_header = algorithm + ' ' + 'Credential=' + self.access_key + '/' + credential_scope + ', ' +  'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature
        
        # The request can include any headers, but MUST include "host", "x-amz-date", 
        # and (for this scenario) "Authorization". "host" and "x-amz-date" must
        # be included in the canonical_headers and signed_headers, as noted
        # earlier. Order here is not significant.
        # Python note: The 'host' header is added automatically by the Python 'requests' library.
        headers = {'x-amz-date':amzdate, 'Authorization':authorization_header, "Accept": "application/json"}
        # ************* SEND THE REQUEST *************
        request_url = self.endpoint + '?' + canonical_querystring
        return request_url, headers
    
    def sendRequest(self, request_parameters, post_data=None):
        request_url, headers = self.getHeaderse(request_parameters)
        print('Request URL = ' + request_url)
        rep = None
        try:
            rep = requests.get(request_url, headers=headers, timeout=10)
            print('Response code: %d\n' % rep.status_code)
        except Exception as e:
            print("headers: %s" % headers)
            traceback.print_exc()
        return rep, headers

''' 
if __name__ == "__main__":
    service = 'iam'
    host = 'iam.cn-shanghai-3.api.ksyun.com'
    region = 'cn-shanghai-3'
    endpoint = 'http://iam.cn-shanghai-3.api.ksyun.com'
    
    # Read AWS access key from env. variables or configuration file. Best practice is NOT
    # to embed credentials in code.
    access_key = "AKLTafg0-VY1SQ2HzX5Hiboa1w"
    secret_key = "OB2ksCy39heVhs+p9tT2YZcRq4iuxCFqz8+JKh7+vXTmpro+cqpA3xl3uXCTf3y/kQ=="

    request_parameters = {
            "Action": "UpdateAccessKey",
            "UserName": "test_user_LdCohvsCSD",
            "AccessKeyId": "AKLTy6gBz46fQxGClXrKS_ASVQ",
            "Status": "Inactive",
            "Version": "2015-11-01"
        }
    
    re = AwsRequest(service, host, region, endpoint, access_key, secret_key)
    re.sendRequest(request_parameters)
'''
if __name__ == "__main__":
    service = 'iam'
    host = 'iam.cn-beijing-6.api.ksyun.com'
    region = 'cn-beijing-6'
    endpoint = 'http://iam.cn-beijing-6.api.ksyun.com'

    # Read AWS access key from env. variables or configuration file. Best practice is NOT
    # to embed credentials in code.
    access_key = "AKLTWtG-bTHOQvq5dtykmUA70g"
    secret_key = "OBUTyr423yW0xW7BStRKWgTkgSKoB7AQ1ySk6XwUSRjzlQE8QoT/P2IHHtFNcCqAmQ=="

    request_parameters = {
        "Action": "UpdateAccessKey",
        "UserName": "test_user_LdCohvsCSD",
        "AccessKeyId": "AKLTWtG-bTHOQvq5dtykmUA70g",
        "Status": "Inactive",
        "Version": "2016-03-04"
    }

    re = AwsRequest(service, host, region, endpoint, access_key, secret_key)
    re.sendRequest(request_parameters)