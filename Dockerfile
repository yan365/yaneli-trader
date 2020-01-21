FROM debian:10

RUN apt-get update -y

RUN apt-get install -y python3-pip python3-pycurl

RUN apt-get install -y git vim gcc adduser

RUN adduser --home /home/trader --system trader

WORKDIR /home/trader/

COPY ./ /home/trader/

USER trader

RUN pip3 install --user -r requirements.txt

