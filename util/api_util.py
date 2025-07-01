import logging
import os
from .aws import AwsRequest
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

root_path = os.getcwd()
# config_file = '%s/config.ini'%root_path
# config = ConfigParser.RawConfigParser()
# with open(config_file,'rb') as f:
#     content = f.read().decode('utf-8-sig').encode('utf-8')
# config.read(config_file)

# username = config.get("user",'username')
# password = config.get('user','password')

# def login(context,url):
#     try:
#
#         #context.driver.switch_to.frame('ksc_login_iframe1')
#
#         context.driver.get('http://www.ksyun.com')
#         time.sleep(2)
#
#         c_dict = get_cookie_from_iam()
#         if c_dict:
#             for keys in c_dict:
#                 name = u"%s" % keys
#                 value = u"%s" % c_dict[keys]
#                 c = {
#                     u'domain': u'.ksyun.com',
#                     u'name': name,
#                     u'value': value,
#                     u'path': u'/',
#                     u'httpOnly': False,
#                     u'secure': False
#                 }
#
#                 context.driver.add_cookie(c)
#
#         #base_url = "https://passport.ksyun.com/"
#         context.driver.get(url)
#         time.sleep(2)
#
#
#     except Exception as e:
#         logging.error(str(e))


def get_cookie_from_iam():
    try:
        service = "iam"
        access_key = os.getenv("access_key")
        secret_key = os.getenv("secret_key")
        region = os.getenv("api_region")
        verison = "2015-11-01"
        endpoint = "http://%s.inner.api.ksyun.com" % service
        host = endpoint.split("//")[1]
        request_parameters = {
            "Action": "GetUserSession",
            "Version": verison
        }
        re = AwsRequest(service, host, region, endpoint, access_key, secret_key)
        resp, header = re.sendRequest(request_parameters)
        if resp and resp.status_code == 200:
            session_url = resp.json()['GetUserSessionResult']['Url']
            r = requests.get(session_url)
            cookies = requests.utils.dict_from_cookiejar(r.cookies)

            return cookies
        else:
            logging.error('failed to get user session url')

    except Exception as e:
        logging.error(str(e))