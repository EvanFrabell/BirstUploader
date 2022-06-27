FROM python:3.7.7

RUN curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
#RUN apt-key adv --keyserver packages.microsoft.com --recv-keys EB3E94ADBE1229CF
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys EB3E94ADBE1229CF
RUN apt-get update
RUN ACCEPT_EULA=Y apt-get -y install unixodbc-dev msodbcsql17
RUN pip install pyodbc
RUN pip install azure.datalake.store
RUN pip install zeep

WORKDIR /opt/birstupload
COPY BirstUpload.py .
COPY SOAPClient.py .
COPY constants.py .
COPY postLS.py .
