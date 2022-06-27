# ManualUploader
 
Repo is to showcase the current script updating Birst weekly/daily.  The script 'ManualUploader' is the focus for when BI engineers need to update any missing data to the dashboard.

1. Run the queries for the datasets you need fixed within their aligned dates and upload the reports to a personal folder to not ruin historical data integrity.

2. Download the files from the Azure file space into Weekly_Dashboard_Upload.  Be cognizant of the directory you store each file.  The directory names must be identical to their source file within Birst (file name does not matter).

Ex: Weekly_Dashboard_Upload > Inline > Inline_parquet_2-22-2022.tsv

3. Update the file env_vars.yaml with the correct password to 'admin_connect' user.

4. Run the script ManualUploader in debug mode using PyCharm. This will help you understand the process which is occurring in case of any error. 

5. After script is finished uploading all of the inserted files, check over the data in the Birst dashboard.  If everything looks correct then proceed to publish 'Weekly' items