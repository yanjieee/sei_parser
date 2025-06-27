#!/usr/bin/env python3
"""
简化版SEI解析器 - 快速提取和显示SEI数据
"""

import struct
import sys
import json


def parse_flv_sei(filepath):
    """从FLV文件中快速提取SEI数据"""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    if data[:3] != b'FLV':
        print("错误: 不是有效的FLV文件")
        return
    
    sei_count = 0
    offset = 13  # 跳过FLV头和第一个previous tag size
    
    while offset < len(data):
        if offset + 11 > len(data):
            break
        
        # 读取FLV tag
        tag_type = data[offset]
        data_size = struct.unpack('>I', b'\x00' + data[offset+1:offset+4])[0]
        
        if tag_type == 9 and offset + 11 + data_size <= len(data):  # 视频tag
            video_data = data[offset+11:offset+11+data_size]
            
            if len(video_data) >= 5 and video_data[0] & 0x0F == 7:  # AVC
                if video_data[1] == 1:  # AVC NALU
                    nalu_data = video_data[5:]
                    sei_count += extract_sei_from_nalus(nalu_data, sei_count)
        
        offset += 11 + data_size + 4


def extract_sei_from_nalus(data, start_count):
    """从NALU数据中提取SEI"""
    count = 0
    offset = 0
    
    while offset + 4 < len(data):
        nalu_length = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        
        if offset + nalu_length > len(data):
            break
        
        nalu = data[offset:offset+nalu_length]
        if len(nalu) > 0 and (nalu[0] & 0x1F) == 6:  # SEI NALU
            count += parse_sei_nalu(nalu, start_count + count + 1)
        
        offset += nalu_length
    
    return count


def parse_sei_nalu(nalu_data, sei_number):
    """解析单个SEI NALU"""
    count = 0
    offset = 1  # 跳过NALU头
    
    while offset < len(nalu_data):
        # 解析SEI type
        sei_type = 0
        while offset < len(nalu_data) and nalu_data[offset] == 0xFF:
            sei_type += 255
            offset += 1
        
        if offset >= len(nalu_data):
            break
        
        sei_type += nalu_data[offset]
        offset += 1
        
        # 解析SEI size
        sei_size = 0
        while offset < len(nalu_data) and nalu_data[offset] == 0xFF:
            sei_size += 255
            offset += 1
        
        if offset >= len(nalu_data):
            break
        
        sei_size += nalu_data[offset]
        offset += 1
        
        # 提取payload
        if offset + sei_size > len(nalu_data):
            sei_size = len(nalu_data) - offset
        
        payload = nalu_data[offset:offset+sei_size]
        
        # 显示SEI信息
        print(f"\n=== SEI #{sei_number + count} ===")
        print(f"类型: {sei_type}")
        print(f"大小: {sei_size} 字节")
        print(f"16进制: {payload.hex()}")
        
        # 尝试解析为字符串
        try:
            clean_payload = payload.rstrip(b'\x00')
            text = clean_payload.decode('utf-8', errors='ignore')
            print(f"字符串: {repr(text)}")
            
            # 尝试解析JSON
            try:
                json_data = json.loads(text)
                print("JSON内容:")
                print(json.dumps(json_data, indent=2, ensure_ascii=False))
            except:
                pass
        except:
            print("字符串: (无法解码)")
        
        print("-" * 50)
        
        offset += sei_size
        count += 1
    
    return count


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python3 simple_sei_parser.py <FLV文件>")
        sys.exit(1)
    
    print("开始解析SEI数据...")
    parse_flv_sei(sys.argv[1])
    print("解析完成！")