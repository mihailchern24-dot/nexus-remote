#pragma once

// Stub: OpenSSL not available
typedef struct ssl_ctx_st SSL_CTX;

bool init_openssl();
void cleanup_openssl();
SSL_CTX* create_server_context();
SSL_CTX* create_client_context();
