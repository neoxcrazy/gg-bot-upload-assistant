import concurrent.futures
import glob
import subprocess
upload_queue = []
for arg_file in glob.glob(f'launch/*'):
    # Since we are in batch mode, we upload every file/folder we find in the path the user specified
    upload_queue.append(arg_file)  # append each item to the list 'upload_queue' now

def run(torrent):
    try:
            bashCommand = f"python3.8 auto_upload.py --path {torrent}"
            process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()
            print(output)
    except:
        pass


upload_queue.sort()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)
futures = [executor.submit(run, item) for item in upload_queue]
concurrent.futures.wait(futures)