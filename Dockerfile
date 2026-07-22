FROM ubuntu:22.04
RUN apt update && apt install -y build-essential cmake libboost-system-dev python3
COPY . /app
WORKDIR /app/build
RUN cmake .. -DBUILD_SHARED_LIBS=OFF
RUN make signaling_server relay_server

EXPOSE 10000 9000

# Python HTTP health check + both servers
CMD python3 -c "from http.server import HTTPServer, BaseHTTPRequestHandler; import os; class H(BaseHTTPRequestHandler): pass; H.do_GET=lambda s: (s.send_response(200), s.send_header('Content-Type','text/plain'), s.end_headers(), s.wfile.write(b'OK')); HTTPServer(('0.0.0.0',int(os.environ.get('PORT',10000))),H).serve_forever()" & ./relay_server 9000 & ./signaling_server 10000 & wait
