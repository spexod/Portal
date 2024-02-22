"""
This file will be used to store the cron jobs for the website.

For example, the function "schedule_deletion" will delete any zip files that are older than 5 minutes.
"""
import os


def schedule_deletion():
    """
    This function will first detect any zip files created by the website. If a file has been created, keep track of
    the time. If the time is greater than 15 minutes, delete the file.
    """

    # Go up one directory to get to the SpExWebsite directory
    os.chdir('/django')
    print(f"Current working directory: {os.getcwd()}")
    # Check if the uploads directory exists
    if os.path.exists('uploads'):
        # If a file gets created, keep track of the time
        for file in os.listdir('uploads'):
            # Print file path
            file_path = os.path.join('uploads', file)
            # If the file is a zip file, delete it
            if file.endswith('.zip') and os.path.getmtime(file_path) > 300.0:
                print('Deleting file: ' + file)
                os.remove(os.path.join('uploads', file))


if __name__ == '__main__':
    schedule_deletion()
