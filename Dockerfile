FROM ubuntu:22.04
RUN apt update && apt install -y build-essential cmake libboost-system-dev
COPY . /app
WORKDIR /app/build
RUN cmake .. -DBUILD_SHARED_LIBS=OFF
RUN make signaling_server relay_server

# Render health check needs HTTP on PORT
# We'll add a simple ncat proxy for health checks
RUN apt install -y ncat netcat-openbsd

EXPOSE 10000 9000

# Start both servers + HTTP health responder on PORT
CMD ./relay_server 9000 & \
    while true; do echo -e "HTTP/1.1 200 OK\r\n\r\nOK" | ncat -l -p \ -c "echo -e 'HTTP/1.1 200 OK\r\n\r\nOK'"; done & \
    ./signaling_server \
