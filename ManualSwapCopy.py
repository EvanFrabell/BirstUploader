import time

import yaml

from SOAPClient import SOAPClient


def main():
    stage_id = '75d23f51-aaeb-41bf-8fa8-a52c78dddcc3'
    prod_id = 'ae77be7c-5d01-48e4-b232-d419be4224cb'

    soap = SOAPClient('https://login.bws.birst.com/CommandWebService.asmx?WSDL')
    admin = 'admin_connect'

    with open("env_vars.yaml", "r") as stream:
        try:
            y = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    # Password is in .yaml file
    password = y['user']['password']

    login_token = soap.login(admin, password)

    stage_status = soap.getLoadStatus(stage_id)
    prod_status = soap.getLoadStatus(prod_id)

    print('Stage Status is ' + stage_status)
    print('Production Status is ' + prod_status)

    if stage_status == 'Available' and prod_status == 'Available':
        print('Go ahead')

        job_token = soap.swapSpaceContents(stage_id, prod_id)

        job_status_attempt = 1
        while job_status_attempt <= 5:
            time.sleep(10)
            try:
                job_completion = soap.isJobComplete(job_token)
                print(job_completion)
                if job_completion:
                    break
            except:
                print('Job not complete')
                job_status_attempt += 1
                continue


if __name__ == "__main__":
    main()
