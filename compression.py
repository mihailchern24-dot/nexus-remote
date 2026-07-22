#!/usr/bin/env python3
# compression.py - ногоуровневое сжатие для Nexus Remote
import zlib
import lzma
import bz2
import gzip
import time
from enum import Enum

class CompressionMethod(Enum):
    NONE = "none"
    ZLIB = "zlib"           # ыстрое, хорошее сжатие
    LZMA = "lzma"           # аксимальное сжатие
    BZ2 = "bz2"             # Среднее
    GZIP = "gzip"           # Совместимое
    LZ4 = "lz4"             # чень быстрое (нужен pip install lz4)
    ZSTD = "zstd"           # учший баланс (нужен pip install zstandard)
    SNAPPY = "snappy"       # Google, быстрое (нужен pip install python-snappy)
    BROTLI = "brotli"       # учшее для web (нужен pip install brotli)

class AdaptiveCompressor:
    """втоматически выбирает лучший метод сжатия"""
    
    # риоритет методов (учитываем скорость и степень сжатия)
    METHODS = [
        CompressionMethod.ZLIB,    # ыстрый, хороший
        CompressionMethod.LZMA,    # аксимальное сжатие
        CompressionMethod.GZIP,    # Стандартный
        CompressionMethod.BZ2,     # Средний
    ]
    
    @staticmethod
    def compress(data, method=CompressionMethod.ZLIB, level=6):
        """Сжать данные выбранным методом"""
        if not data:
            return data, CompressionMethod.NONE
        
        try:
            if method == CompressionMethod.ZLIB:
                compressed = zlib.compress(data, level)
            elif method == CompressionMethod.LZMA:
                compressed = lzma.compress(data)
            elif method == CompressionMethod.BZ2:
                compressed = bz2.compress(data, level)
            elif method == CompressionMethod.GZIP:
                compressed = gzip.compress(data, level)
            elif method == CompressionMethod.LZ4:
                import lz4.frame
                compressed = lz4.frame.compress(data)
            elif method == CompressionMethod.ZSTD:
                import zstandard as zstd
                cctx = zstd.ZstdCompressor(level=level)
                compressed = cctx.compress(data)
            elif method == CompressionMethod.SNAPPY:
                import snappy
                compressed = snappy.compress(data)
            elif method == CompressionMethod.BROTLI:
                import brotli
                compressed = brotli.compress(data)
            else:
                return data, CompressionMethod.NONE
            
            # сли сжатие неэффективно, возвращаем оригинал
            if len(compressed) >= len(data):
                return data, CompressionMethod.NONE
            
            return compressed, method
        
        except ImportError:
            # сли библиотека не установлена, пробуем zlib
            try:
                compressed = zlib.compress(data, level)
                return compressed, CompressionMethod.ZLIB
            except:
                return data, CompressionMethod.NONE
    
    @staticmethod
    def decompress(data, method):
        """аспаковать данные"""
        if not data or method == CompressionMethod.NONE:
            return data
        
        try:
            if method == CompressionMethod.ZLIB:
                return zlib.decompress(data)
            elif method == CompressionMethod.LZMA:
                return lzma.decompress(data)
            elif method == CompressionMethod.BZ2:
                return bz2.decompress(data)
            elif method == CompressionMethod.GZIP:
                return gzip.decompress(data)
            elif method == CompressionMethod.LZ4:
                import lz4.frame
                return lz4.frame.decompress(data)
            elif method == CompressionMethod.ZSTD:
                import zstandard as zstd
                dctx = zstd.ZstdDecompressor()
                return dctx.decompress(data)
            elif method == CompressionMethod.SNAPPY:
                import snappy
                return snappy.decompress(data)
            elif method == CompressionMethod.BROTLI:
                import brotli
                return brotli.decompress(data)
        except:
            return data
    
    @staticmethod
    def best_compress(data, speed_priority=True):
        """втоматически выбрать лучший метод сжатия"""
        best_compressed = data
        best_method = CompressionMethod.NONE
        best_size = len(data)
        
        for method in AdaptiveCompressor.METHODS:
            try:
                start = time.time()
                compressed, _ = AdaptiveCompressor.compress(data, method)
                elapsed = time.time() - start
                
                if len(compressed) < best_size:
                    best_compressed = compressed
                    best_method = method
                    best_size = len(compressed)
            except:
                continue
        
        ratio = (1 - best_size / len(data)) * 100 if len(data) > 0 else 0
        return best_compressed, best_method, ratio

# Тесты сжатия
if __name__ == "__main__":
    # Тестовые данные (имитация кадра экрана)
    test_data = b"A" * 100000 + b"B" * 50000 + b"C" * 25000  # 175KB
    
    print("=== Тесты сжатия ===\n")
    
    for method in [CompressionMethod.ZLIB, CompressionMethod.LZMA, 
                   CompressionMethod.GZIP, CompressionMethod.BZ2]:
        compressed, _ = AdaptiveCompressor.compress(test_data, method)
        ratio = (1 - len(compressed) / len(test_data)) * 100
        print(f"{method.value:10} | {len(test_data):>6} -> {len(compressed):>6} bytes | {ratio:.1f}% сжатия")
    
    print("\n=== вто-выбор лучшего метода ===")
    best_data, best_method, ratio = AdaptiveCompressor.best_compress(test_data)
    print(f"учший: {best_method.value} | {ratio:.1f}% сжатия | {len(best_data)} bytes")
