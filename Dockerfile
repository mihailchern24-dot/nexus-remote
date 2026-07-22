FROM ubuntu:22.04
RUN apt update && apt install -y build-essential cmake libboost-system-dev python3
COPY . /app
WORKDIR /app/build
RUN cmake .. -DBUILD_SHARED_LIBS=OFF
RUN make signaling_server relay_server

EXPOSE 10000 9000

# Start Python HTTP server for health checks + both servers
CMD python3 -m http.server \ --bind 0.0.0.0 & ./relay_server 9000 & ./signaling_server 10000 & wait
