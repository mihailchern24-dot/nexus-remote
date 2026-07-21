#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <vector>

std::array<unsigned char, 20> sha1(const std::vector<unsigned char> &data);
std::array<unsigned char, 20> sha1(const std::string &text);
