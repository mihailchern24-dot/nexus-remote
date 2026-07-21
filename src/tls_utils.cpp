#include "../include/tls_utils.h"

// Stub: OpenSSL not available
bool init_openssl() { return true; }
void cleanup_openssl() {}
SSL_CTX* create_server_context() { return nullptr; }
SSL_CTX* create_client_context() { return nullptr; }
