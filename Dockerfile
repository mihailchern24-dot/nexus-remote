FROM ubuntu:22.04
RUN apt update && apt install -y build-essential cmake libboost-system-dev
COPY . /app
WORKDIR /app/build
RUN cmake .. -DBUILD_SHARED_LIBS=OFF
RUN make signaling_server relay_server

EXPOSE 10000 9000

# Start relay in background, signaling on PORT
CMD ./relay_server 9000 & ./signaling_server \
