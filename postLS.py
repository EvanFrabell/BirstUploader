import sys, json, requests, socket
from datetime import datetime

def postLS(msg, env):
	if (env=='TEST'): return
	url = 'https://%LOGSTASH_USER%:%LOGSTASH_PASS%@logs-input.cnetcontent.com'
	data = json.dumps({
		'events': [{
			'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
			'Level': 'Information',
	 		'Properties': {
				'Host': socket.gethostname(),
				'App': 'BirstUpload',
				'Env': env
			},
			'RenderedMessage': msg
		}]
 	})
	headers = {'Content-type': 'application/json'}
	return(requests.post(url = url, headers = headers, data = data).status_code)

def main():
	postLS('Test message', 'TEST')
	sys.exit(0)

if __name__ == "__main__":
	main()