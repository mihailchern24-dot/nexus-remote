#pragma once
#include <string>

namespace nexus::wol {

// Отправляет Magic Packet на MAC-адрес
// mac: "AA:BB:CC:DD:EE:FF" или "AABBCCDDEEFF"
bool send_magic_packet(const std::string& mac_address);

} // namespace nexus::wol
