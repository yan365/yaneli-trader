FROM fedora:29

RUN dnf update -y

RUN dnf install -y glibc-devel gcc gcc-c++ make libtool curl

RUN dnf install -y python3-pip python3-devel python3-pycurl

RUN dnf install -y git vim 

RUN adduser -m -d /home/trader trader

WORKDIR /home/trader

RUN pip3 install --user -r requirements.txt

COPY ./ /home/trader/source
