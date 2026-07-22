FROM ubuntu:22.04
RUN apt update && apt install -y build-essential cmake libboost-system-dev python3 python3-pip
RUN pip3 install cryptography==41.0.7 pillow lz4 zstandard brotli python-snappy || true
COPY . /app
WORKDIR /app/build
RUN cmake .. -DBUILD_SHARED_LIBS=OFF
RUN make signaling_server relay_server

EXPOSE 10000 9000 8080

CMD python3 /app/http_signaling.py & ./relay_server 9000 & ./signaling_server 8080 & wait
