FROM fedora:42

WORKDIR /app

ADD ./ta-lib-deps/ta-lib-0.6.3-src.tar.gz .
COPY ./python-deps/requirements.txt .

RUN dnf -y install python3 && \
    dnf -y install python3-devel && \ 
    dnf -y install python3-pip && \ 
    dnf -y install gcc && \
    dnf -y install sleep && \
    cd ta-lib-0.6.3 && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    pip install -r /app/requirements.txt

ENTRYPOINT ["/bin/bash"]
