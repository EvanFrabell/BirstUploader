import os
import sys
import time
from itertools import islice
import yaml

from SOAPClient import SOAPClient


def upload_chunks(soap, upload_token, data):
    attempt = 1
    while attempt <= 5:
        if attempt > 1:
            print('blow_chunks attempt: ' + str(attempt))
        try:
            soap.uploadData(upload_token, len(data), data)
            break
        except:
            print('blow_chunks fail: ' + str(sys.exc_info()[1]), 'es')
            attempt += 1
    if attempt >= 5:
        print('uploadChunk failed after ' + str(5) + ' attempt(s)', 'es msg')
        return True
    return False


def main():
    space_id = '75d23f51-aaeb-41bf-8fa8-a52c78dddcc3'
    # DEV 75d23f51-aaeb-41bf-8fa8-a52c78dddcc3
    # STAGE MANUAL FIX 71775195-03e0-489c-954f-6fff703b3522
    # 0527TEST f7cf3ca0-3c61-488f-9150-bd28b06d708e
    # STAGE2TEST '0223271b-9f88-4cd0-8acb-37f076a5914e'
    # STAGE '37d7d286-1e87-40a6-9766-43e3899467e7'

    soap = SOAPClient('https://login.bws.birst.com/CommandWebService.asmx?WSDL')
    admin = 'admin_connect'

    with open("env_vars.yaml", "r") as stream:
        try:
            y = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    # Password is in .yaml file
    password = y['user']['password']

    # Already done:
    # Weekly_AR should be wary!
    # 'Asset', 'Cpn', 'DCCN', 'Ficon', 'FiconUrl', 'Finder', 'HPE', 'Inline', 'Labels', 'Logo', 'LogoURL',
    #                    'Missed',
    #                    'Request',
    #                    'URL', 'Weekly_AR'
    # 'Asset', 'Cpn', 'DCCN', 'Ficon', 'FiconUrl', 'Finder', 'HPE', 'Inline', 'Labels', 'Logo', 'LogoURL',
    #                    'Missed',
    #                    'Request',
    #                    'URL',
    source_list = ['Weekly_AR']

    first_file = True
    for source in source_list:
        print('########SOURCE######## ' + source + ' #############')

        login_token = soap.login(admin, password)
        print('Login Token: ' + login_token)
        status = soap.getLoadStatus(space_id)

        while status != 'Available':
            # Wait for upload status to be available and re-run script.  This may take a minute or two.
            print('STOP TO DEBUG - BREAKPOINT')

        upload_token = soap.beginDataUpload(space_id, source)
        print(upload_token)

        soap.setDataUploadOptions(upload_token, 'IgnoreQuotesNotAtStartOrEnd=true'.split())

        dir_path = 'Weekly_Dashboard_Upload/' + source
        file_name = os.listdir(dir_path)[0]
        path = str(dir_path + '/' + file_name)
        file_size = os.path.getsize(path)
        print(file_size)

        uploaded_bytes = {file_name: 0}

        f = open(path, 'rb')
        if first_file:
            first_file = False
        else:
            lines = list(islice(f, 1))
            uploaded_bytes[file_name] += len(lines[0])

        while True:
            strings_in_chunk = 64 * 1024
            lines = list(islice(f, strings_in_chunk))
            if not lines:
                break
            data = b''.join(lines)
            lines = None

            if upload_chunks(soap, upload_token, data):
                break

            uploaded_bytes[file_name] += len(data)
            print(file_name + ' uploaded ' + '{:.2%}'.format(uploaded_bytes[file_name] / file_size))

        try:
            soap.finishDataUpload(upload_token)
        except:
            print('Cannot finish upload')

        first_file = True
        f.close()
        soap.logout()
        time.sleep(45)

    print('Terminated!')
    # soap.cancelDataUpload()
    soap.logout()
    sys.exit(0)


if __name__ == "__main__":
    main()
