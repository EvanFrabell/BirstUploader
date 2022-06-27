import sys, os, gc, configparser, argparse, time
import logging
from SOAPClient import SOAPClient
from postLS import postLS
from itertools import islice
from datetime import datetime
import constants
import signal
import pyodbc


def check():
    cts = datetime.utcnow()
    postLog('Current TS (UTC): ' + cts.strftime('%Y-%m-%d %H:%M:%S'), 'buf')
    cn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};' + config['TS Checks']['connectString'])
    cursor = cn.cursor()
    ready = True
    cursor.execute(config['TS Checks']['query'])
    row = cursor.fetchone()
    while row:
        st = ' - Not ready'
        if (sameDay(cts, row[1])):
            st = ' - OK'
        else:
            ready = False
        postLog(row[0] + ' (UTC): ' + str(row[1]) + st, 'buf')
        row = cursor.fetchone()
    return (ready)


def sameDay(d1, d2):
    if (constants.dryrun): return (True)
    if (d1.year == d2.year and d1.month == d2.month and d1.day == d2.day): return (True)
    return (False)


def wait4space(spaceID):
    bcSOAP.login(config['Birst']['user'], config['Birst']['pass'])
    status = bcSOAP.getLoadStatus(spaceID)
    bcSOAP.logout()
    while (status != 'Available'):
        postLog('Space ' + spaceID + ' is ' + status)
        time.sleep(constants.space_waitTime * 2)
        bcSOAP.login(config['Birst']['user'], config['Birst']['pass'])
        status = bcSOAP.getLoadStatus(spaceID)
        bcSOAP.logout()
        if (status == 'Available'): time.sleep(constants.space_waitTime)
    postLog('Space ' + spaceID + ' is ' + status, 'ps')


def upload():
    wait4space(config['Birst']['upload_spaceID'])
    loginToken = bcSOAP.login(config['Birst']['user'], config['Birst']['pass'])
    print('Login token: ' + loginToken)
    for upload in config['Uploads']:
        attempt = 1
        while (attempt <= constants.attempts):
            failedState = False
            if (attempt > 1): postLog('Attempt: ' + str(attempt), 'es msg')
            try:
                uplToken = bcSOAP.beginDataUpload(config['Birst']['upload_spaceID'], upload)
            except:
                postLog('beginDataUpload fail: ' + str(sys.exc_info()[1]), 'es msg')
                if (not constants.dryrun): time.sleep(constants.longJob_waitTime * attempt)
                attempt += 1
                continue
            print('Upload token: ' + uplToken)
            bcSOAP.setDataUploadOptions(uplToken, 'IgnoreQuotesNotAtStartOrEnd=true'.split())
            uploadStart = time.time()
            global uploadedBytes
            uploadedBytes = {}
            firstFile = True
            for item in getFilesList(config['Uploads'][upload]):
                if (item['type'] != 'FILE'):
                    postLog('Skipped: ' + item['name'], 'es msg')
                    continue
                downloadFile(item['name'])
                fileName = os.path.basename(item['name'])
                fileSize = os.path.getsize(config['Common']['tmpFolder'] + '/' + fileName)
                postLog('Uploading ' + item['name'] + ' (' + '{:.2f}'.format(
                    fileSize / 1024 / 1024) + 'MB)' + ' to ' + upload, 'es')
                uploadedBytes[fileName] = 0
                inFile = open(config['Common']['tmpFolder'] + '/' + fileName, 'rb')
                if (firstFile):
                    firstFile = False
                else:
                    lines = list(islice(inFile, 1))
                    uploadedBytes[fileName] += len(lines[0])
                while True:
                    lines = list(islice(inFile, constants.strings_in_chunk))
                    if not lines:
                        break
                    data = b''.join(lines)
                    lines = None
                    if (not uploadChunk(fileName, fileSize, uplToken, data)):
                        failedState = True
                        break
                    uploadedBytes[fileName] += len(data)
                    postLog(fileName + ' uploaded ' + '{:.2%}'.format(uploadedBytes[fileName] / fileSize))
                inFile.close()
                if (not constants.keepFiles): os.remove(config['Common']['tmpFolder'] + '/' + fileName)
                if (failedState): break
            # post file done:
            postLog('Upload done: ' + upload, 'es')
            if (not finishDataUpload(uplToken)):
                attempt += 1
                continue
            jobStatusAttempt = 1
            while (jobStatusAttempt <= constants.attempts):
                if (not constants.dryrun): time.sleep(constants.shortJob_waitTime)
                try:
                    status = bcSOAP.getJobStatus(uplToken)
                    postLog(status.statusCode)
                    if (status.statusCode == 'Failed'):
                        print(status.message, 'es msg')
                        failedState = True
                        break
                    if (bcSOAP.isJobComplete(uplToken)): break
                    jobStatusAttempt = 1
                except:
                    postLog('getJobStatus fail: ' + str(sys.exc_info()[1]), 'es')
                    jobStatusAttempt += 1
                    continue
            if (jobStatusAttempt >= constants.attempts):
                postLog('Can\'t get jobStatus. Too many errors', 'es msg')
                failedState = True
            if (failedState):
                postLog('Upload failed: ' + upload + ' [' + '{:.2f}'.format(time.time() - uploadStart) + ']', 'es')
                attempt += 1
            else:
                postLog('Upload finished: ' + upload + ' [' + '{:.2f}'.format(time.time() - uploadStart) + ']',
                        'es msg')
                break
        if (attempt >= constants.attempts):
            postLog('Upload to ' + upload + ' failed after ' + str(constants.attempts) + ' attempt(s)', 'es msg')
            return (False)
    bcSOAP.logout()
    return (True)


def uploadChunk(fileName, fileSize, uplToken, data):
    attempt = 1
    while (attempt <= constants.attempts):
        if (attempt > 1): postLog('uploadChunk attempt: ' + str(attempt), 'es')
        try:
            bcSOAP.uploadData(uplToken, len(data), data)
            break
        except:
            postLog('uploadChunk fail: ' + str(sys.exc_info()[1]), 'es')
            if (not constants.dryrun): time.sleep(constants.shortJob_waitTime * attempt)
            attempt += 1
    if (attempt >= constants.attempts):
        postLog('uploadChunk failed after ' + str(constants.attempts) + ' attempt(s)', 'es msg')
        return (False)
    return (True)


def finishDataUpload(uplToken):
    attempt = 1
    while (attempt <= constants.attempts):
        if (attempt > 1): postLog('finishDataUpload attempt: ' + str(attempt), 'es')
        try:
            bcSOAP.finishDataUpload(uplToken)
            break
        except:
            postLog('finishDataUpload fail: ' + str(sys.exc_info()[1]), 'es')
            if (not constants.dryrun): time.sleep(constants.shortJob_waitTime * attempt)
            attempt += 1
    if (attempt >= constants.attempts):
        postLog('finishDataUpload failed after ' + str(constants.attempts) + ' attempt(s)', 'es msg')
        return (False)
    return (True)


def getFilesList(folder):
    from azure.datalake.store import core, lib
    adlCreds = lib.auth(tenant_id=config['DataLake']['tenantId'], client_id=config['DataLake']['clientId'],
                        client_secret=config['DataLake']['clientKey'])
    adlsFileSystemClient = core.AzureDLFileSystem(adlCreds, store_name=config['DataLake']['account'])
    folderContents = []
    attempt = 1
    while (attempt <= constants.attempts):
        if (attempt > 1): postLog('getFilesList attempt: ' + str(attempt), 'es')
        folderContents = []
        try:
            folderContents = adlsFileSystemClient.ls(folder, detail=True)
            break
        except:
            postLog('getFilesList fail: ' + str(sys.exc_info()[1]), 'es')
            attempt += 1
    if (attempt >= constants.attempts):
        postLog('getFilesList failed after ' + str(constants.attempts) + ' attempt(s)', 'es msg')
        sendEmail('FAILED!')
        sys.exit(0)
    return (folderContents)


def downloadFile(fl):
    if (os.path.isfile(config['Common']['tmpFolder'] + '/' + os.path.basename(fl))):
        postLog('File ' + fl + ' already exists', 'es msg')
        return
    if (constants.dryrun):
        with open(config['Common']['tmpFolder'] + '/' + os.path.basename(fl), 'w') as fakeFile:
            fakeFile.write('Header\r\n')
            fakeFile.write('Data\r\n')
        return
    from azure.datalake.store import core, lib, multithread
    postLog('Downloading ' + fl, 'es')
    attempt = 1
    while (attempt <= constants.attempts):
        if (attempt > 1): postLog('Retry: ' + str(attempt), 'es msg')
        try:
            adlCreds = lib.auth(tenant_id=config['DataLake']['tenantId'], client_id=config['DataLake']['clientId'],
                                client_secret=config['DataLake']['clientKey'])
            adlsFileSystemClient = core.AzureDLFileSystem(adlCreds, store_name=config['DataLake']['account'])
        except:
            attempt += 1
            continue
        fileDownloadStart = time.time()
        try:
            multithread.ADLDownloader(adlsFileSystemClient, lpath=config['Common']['tmpFolder'],
                                      rpath=fl, nthreads=4, chunksize=16777216, blocksize=2097152, overwrite=True)
            break
        except:
            postLog('downloadFile fail: ' + str(sys.exc_info()[1]), 'es')
            attempt += 1
            continue
    if (attempt >= constants.attempts):
        postLog('downloadFile failed after ' + str(constants.attempts) + ' attempt(s)', 'es')
        sendEmail('FAILED!')
        sys.exit(0)
    postLog('Download finished: ' + fl + ' [' + '{:.2f}'.format(time.time() - fileDownloadStart) + ']', 'es')


def process():
    wait4space(config['Birst']['upload_spaceID'])
    bcSOAP.login(config['Birst']['user'], config['Birst']['pass'])
    groups = config.get('Birst', 'processGroups', fallback='All').split()
    postLog('Processing: ' + str(groups), 'es msg')
    if (groups[0] == 'All'): groups = []
    jobStart = time.time()
    jobToken = bcSOAP.publishData(config['Birst']['upload_spaceID'], groups, datetime.now())
    failedState = False
    jobStatusAttempt = 1
    while (jobStatusAttempt <= constants.attempts):
        if (not constants.dryrun): time.sleep(constants.shortJob_waitTime)
        try:
            status = bcSOAP.getJobStatus(jobToken)
            postLog(status.statusCode)
            if (status.statusCode == 'Failed'):
                postLog(status.message, 'es msg')
                failedState = True
                break
            if (bcSOAP.isJobComplete(jobToken)): break
        except:
            postLog('getJobStatus fail: ' + str(sys.exc_info()[1]), 'es msg')
            jobStatusAttempt += 1
            continue
    bcSOAP.logout()
    if (jobStatusAttempt >= constants.attempts):
        postLog('Can\'t get jobStatus. Too many errors', 'es msg')
        return (False)
    if (failedState):
        postLog('Processing failed', 'es msg')
        return (False)
    else:
        postLog('Processing done [' + '{:.2f}'.format(time.time() - jobStart) + ']', 'es msg')
        return (True)


def swap():
    wait4space(config['Birst']['upload_spaceID'])
    wait4space(config['Birst']['main_spaceID'])
    bcSOAP.login(config['Birst']['user'], config['Birst']['pass'])
    postLog('Swap started', 'es msg')
    jobStart = time.time()
    jobToken = bcSOAP.swapSpaceContents(config['Birst']['upload_spaceID'], config['Birst']['main_spaceID'])
    failedState = False
    jobStatusAttempt = 1
    while (jobStatusAttempt <= constants.attempts):
        if (not constants.dryrun): time.sleep(constants.shortJob_waitTime)
        try:
            status = bcSOAP.getJobStatus(jobToken)
            postLog(status.statusCode)
            if (status.statusCode == 'Failed'):
                postLog(status.message, 'es msg')
                failedState = True
                break
            if (bcSOAP.isJobComplete(jobToken)): break
        except:
            postLog('getJobStatus fail: ' + str(sys.exc_info()[1]), 'es msg')
            jobStatusAttempt += 1
            continue
    bcSOAP.logout()
    if (jobStatusAttempt >= constants.attempts):
        postLog('Can\'t get jobStatus. Too many errors', 'es msg')
        return (False)
    if (failedState):
        postLog('Swap failed', 'es msg')
        return (False)
    else:
        postLog('Swap done [' + '{:.2f}'.format(time.time() - jobStart) + ']', 'es msg')
        return (True)


def copy():
    wait4space(config['Birst']['upload_spaceID'])
    wait4space(config['Birst']['main_spaceID'])
    bcSOAP.login(config['Birst']['user'], config['Birst']['pass'])
    postLog('Copy started. ' + config['Birst']['main_spaceID'] + ' => ' + config['Birst']['upload_spaceID'], 'es msg')
    jobStart = time.time()
    jobToken = bcSOAP.copySpaceContents(config['Birst']['main_spaceID'], config['Birst']['upload_spaceID'])
    failedState = False
    jobStatusAttempt = 1
    while (jobStatusAttempt <= constants.attempts):
        if (not constants.dryrun): time.sleep(constants.shortJob_waitTime)
        try:
            status = bcSOAP.getJobStatus(jobToken)
            postLog(status.statusCode)
            if (status.statusCode == 'Failed'):
                postLog(status.message, 'es msg')
                failedState = True
                break
            if (bcSOAP.isJobComplete(jobToken)): break
        except:
            postLog('getJobStatus fail: ' + str(sys.exc_info()[1]), 'es msg')
            jobStatusAttempt += 1
            continue
    bcSOAP.logout()
    if (jobStatusAttempt >= constants.attempts):
        postLog('Can\'t get jobStatus. Too many errors', 'es msg')
        return (False)
    if (failedState):
        postLog('Copy failed', 'es msg')
        return (False)
    else:
        postLog('Copy done [' + '{:.2f}'.format(time.time() - jobStart) + ']', 'es msg')
        return (True)


def main():
    parser = argparse.ArgumentParser()


    parser.add_argument('-dryrun', dest='dryrun', action='store_true', default=False)
    # parser.set_defaults(dryrun = False)
    parser.add_argument('-noemail', dest='noemail', action='store_true', default=False)
    # parser.set_defaults(noemail = False)
    parser.add_argument('-config')
    # parser.add_argument('-steps', required=True)
    args = parser.parse_args()
    # steps = args.steps.split()
    constants.dryrun = args.dryrun
    constants.noemail = args.noemail

    global config
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(args.config)
    os.makedirs(config['Common']['tmpFolder'], exist_ok=True)

    global logBuffer
    logBuffer = ''
    global logMsgBuffer
    logMsgBuffer = ''
    global bcSOAP
    bcSOAP = SOAPClient(config['Birst']['SOAPUrl'] + '?WSDL')

    for s in steps:
        if (s == 'check'):
            while (not check()):
                postLog('TS is not ready! Next try in ' + str(constants.ts_waitTime) + ' minutes', 'buf')
                postLog('', 'buf es')
                time.sleep(constants.ts_waitTime * 60)
            postLog('', 'es msg')
            sendEmail('Upload started')
        elif (s == 'wait'):
            wait4space(config['Birst']['upload_spaceID'])
        elif (s == 'upload'):
            if (upload()):
                sendEmail('Upload done')
            else:
                sendEmail('Upload FAILED!')
                sys.exit(0)
        elif (s == 'process'):
            if (process()):
                sendEmail('Processing done')
            else:
                sendEmail('Processing FAILED!')
                sys.exit(0)
        elif (s == 'swap'):
            if (swap()):
                sendEmail('Swap done')
            else:
                sendEmail('Swap FAILED!')
                sys.exit(0)
        elif (s == 'copy'):
            if (copy()):
                sendEmail('Copy done')
            else:
                sendEmail('Copy FAILED!')
                sys.exit(0)
        else:
            print('Unknown step: ' + s)
    postLog('All done', 'es msg')
    sendEmail('All done')


def postLog(msg, options=''):
    lsEnv = 'PROD'
    if (constants.dryrun): lsEnv = 'TEST'
    global logBuffer
    global logMsgBuffer
    if (msg == ''):
        for o in options.split():
            if (o == 'msg'): logMsgBuffer += logBuffer
            if (o == 'es'): postLS(logBuffer, lsEnv)
        logBuffer = ''
        return
    st = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + ' * ' + msg
    for o in options.split():
        if (o == 'buf'): logBuffer += (st + '\n')
        if (o == 'es'): postLS(st, lsEnv)
        if (o == 'msg'): logMsgBuffer += (st + '\n')
    print(st)


def sendEmail(subj):
    global logMsgBuffer
    print('Sending email')
    if (constants.dryrun or constants.noemail): return
    body = 'From: ' + 'birstupload@cnetcontent.com' + '\n' + \
           'To: ' + ','.join(config['Mail']['to'].split()) + '\n' + \
           'Subject: BirstUpload (' + config['Mail']['subjPrefix'] + ') - ' + subj + '\n\n' + \
           logMsgBuffer
    import smtplib
    server = smtplib.SMTP(config['Mail']['host'], config['Mail']['port'])
    server.starttls()
    server.login(config['Mail']['user'], config['Mail']['pass'])
    server.sendmail('noreply@cnetcontent.com', config['Mail']['to'].split(), body)
    server.quit()


def setupLogging(defLevel='WARNING'):
    logLevel = os.environ.get('LOG_LEVEL', defLevel)
    levels = dict(
        CRITICAL=logging.CRITICAL,
        ERROR=logging.ERROR,
        WARNING=logging.WARNING,
        INFO=logging.INFO,
        DEBUG=logging.DEBUG)
    if logLevel in levels:
        logLevel = levels[logLevel]
    else:
        sys.exit("invalid LOG_LEVEL '{0}'".format(logLevel))
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: %(message)s', level=logLevel)


# logging.basicConfig(filename = 'log.txt', format = '%(asctime)s %(name)s %(levelname)s: %(message)s', level = logLevel)

def stopHandler(signal, frame):
    print('Terminated!')
    bcSOAP.cancelDataUpload()
    bcSOAP.logout()
    sys.exit(0)


signal.signal(signal.SIGTERM, stopHandler)
signal.signal(signal.SIGINT, stopHandler)

if __name__ == "__main__":
    # setupLogging('DEBUG')
    setupLogging()
    main()
