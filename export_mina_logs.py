import os
import boto3
import yaml
from botocore.exceptions import NoCredentialsError
import time

c = yaml.load(open('/root/mina_utils/config.yml', encoding='utf8'), Loader=yaml.SafeLoader)

NODE_NAME           = str(c["NODE_NAME"])
ACCESS_KEY      = str(c["AWS_ACCESS_KEY"])
SECRET_KEY      = str(c["AWS_SECRET_KEY"])

current_time = time.strftime("%Y%m%d_%H%M")

fn = NODE_NAME + '_mina_log_' + str(current_time)
local_file = '/root/.mina-config/exported_logs/' + fn + '.tar.gz'

bucket_name = 'mina-node-logs'
s3_file_name = fn + '.tar.gz'



def upload_to_aws(local_file, bucket, s3_file):
    s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY)

    try:
        s3.upload_file(local_file, bucket, s3_file)
        print("Upload Successful")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

if __name__ == "__main__": 

    try:    
        command = 'mina client export-logs -tarfile ' + fn
        run_export = os.system(command) # executing the shell command to export the logs
        if run_export == 0: # the shell command returns 0 if the run was success
            uploaded = upload_to_aws(local_file, bucket_name, s3_file_name)
        else:
            print("execution of export-logs failed")

    except Exception as e:
        print('some random issue : ' + str(e))
