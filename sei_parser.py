#!/usr/bin/env python3
"""
H.264/H.265 SEI Parser
支持从FLV、MP4、H.264裸流等文件中解析SEI数据
"""

import struct
import sys
import os
import json
from typing import List, Tuple, Optional, Dict, Any


class SEIParser:
    def __init__(self):
        self.sei_types = {
            0: "buffering_period",
            1: "pic_timing",
            2: "pan_scan_rect",
            3: "filler_payload",
            4: "user_data_registered_itu_t_t35",
            5: "user_data_unregistered",
            6: "recovery_point",
            7: "dec_ref_pic_marking_repetition",
            8: "spare_pic",
            9: "scene_info",
            10: "sub_seq_info",
            11: "sub_seq_layer_characteristics",
            12: "sub_seq_characteristics",
            13: "full_frame_freeze",
            14: "full_frame_freeze_release",
            15: "full_frame_snapshot",
            16: "progressive_refinement_segment_start",
            17: "progressive_refinement_segment_end",
            18: "motion_constrained_slice_group_set",
            19: "film_grain_characteristics",
            20: "deblocking_filter_display_preference",
            21: "stereo_video_info",
            22: "post_filter_hint",
            23: "tone_mapping_info",
            24: "scalability_info",
            25: "sub_pic_scalable_layer",
            26: "non_required_layer_rep",
            27: "priority_layer_info",
            28: "layers_not_present",
            29: "layer_dependency_change",
            30: "scalable_nesting",
            31: "base_layer_temporal_hrd",
            32: "quality_layer_integrity_check",
            33: "redundant_pic_property",
            34: "tl0_dep_rep_index",
            35: "tl_switching_point",
            36: "parallel_decoding_info",
            37: "mvc_scalable_nesting",
            38: "view_scalability_info",
            39: "multiview_scene_info",
            40: "multiview_acquisition_info",
            41: "non_required_view_component",
            42: "view_dependency_change",
            43: "operation_points_not_present",
            44: "base_view_temporal_hrd",
            45: "frame_packing_arrangement",
            46: "multiview_view_position",
            47: "display_orientation",
            48: "mvcd_scalable_nesting",
            49: "mvcd_view_scalability_info",
            50: "depth_representation_info",
            51: "three_dimensional_reference_displays_info",
            52: "depth_timing",
            53: "depth_sampling_info",
            54: "constrained_depth_parameter_set_identifier",
            # H.265 specific
            128: "active_parameter_sets",
            129: "decoding_unit_info",
            130: "temporal_sub_layer_zero_index",
            131: "decoded_picture_hash",
            132: "scalable_nesting",
            133: "region_refresh_info",
            134: "no_display",
            135: "time_code",
            136: "mastering_display_colour_volume",
            137: "segmented_rect_frame_packing_arrangement",
            138: "temporal_motion_constrained_tile_sets",
            139: "chroma_resampling_filter_hint",
            140: "knee_function_info",
            141: "colour_remapping_info",
            142: "deinterlaced_field_identification",
            143: "content_light_level_info",
            144: "dependent_rap_indication",
            145: "coded_region_completion",
            146: "alternative_transfer_characteristics",
            147: "ambient_viewing_environment",
            148: "content_colour_volume",
            149: "equirectangular_projection",
            150: "cubemap_projection",
            151: "fisheye_video_info",
            152: "sphere_rotation",
            153: "regionwise_packing",
            154: "omni_viewport",
            155: "regional_nesting",
            156: "mcts_extraction_info_sets",
            157: "mcts_extraction_info_nesting",
            158: "layers_not_present",
            159: "inter_layer_constrained_tile_sets",
            160: "bsp_nesting",
            161: "bsp_initial_arrival_time",
            162: "sub_bitstream_property",
            163: "alpha_channel_info",
            164: "overlay_info",
            165: "temporal_mv_prediction_constraints",
            166: "frame_field_info",
            167: "three_dimensional_reference_displays_info",
            168: "depth_representation_info_sei",
            169: "multiview_scene_info",
            170: "multiview_acquisition_info",
            171: "multiview_view_position",
            172: "alternative_depth_info",
        }
    
    def parse_file(self, filepath: str) -> List[Dict[str, Any]]:
        """解析文件中的SEI数据"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        file_ext = os.path.splitext(filepath)[1].lower()
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        if file_ext == '.flv':
            return self._parse_flv(data)
        elif file_ext == '.mp4':
            return self._parse_mp4(data)
        elif file_ext in ['.h264', '.264']:
            return self._parse_h264_stream(data)
        elif file_ext in ['.h265', '.265', '.hevc']:
            return self._parse_h265_stream(data)
        else:
            # 尝试自动检测
            return self._auto_detect_and_parse(data)
    
    def _parse_flv(self, data: bytes) -> List[Dict[str, Any]]:
        """解析FLV文件"""
        sei_list = []
        
        # FLV文件头
        if len(data) < 9 or data[:3] != b'FLV':
            raise ValueError("不是有效的FLV文件")
        
        offset = 9  # 跳过FLV头
        offset += 4  # 跳过第一个previous tag size
        
        while offset < len(data):
            if offset + 11 > len(data):
                break
                
            # 读取FLV tag头
            tag_type = data[offset]
            data_size = struct.unpack('>I', b'\x00' + data[offset+1:offset+4])[0]
            timestamp = struct.unpack('>I', b'\x00' + data[offset+4:offset+7])[0]
            timestamp_ext = data[offset+7]
            stream_id = struct.unpack('>I', b'\x00' + data[offset+8:offset+11])[0]
            
            offset += 11
            
            if offset + data_size > len(data):
                break
            
            # 只处理视频tag (type = 9)
            if tag_type == 9:
                video_data = data[offset:offset+data_size]
                if len(video_data) > 0:
                    sei_data = self._extract_sei_from_video_data(video_data)
                    sei_list.extend(sei_data)
            
            offset += data_size + 4  # 数据 + previous tag size
        
        return sei_list
    
    def _extract_sei_from_video_data(self, video_data: bytes) -> List[Dict[str, Any]]:
        """从视频数据中提取SEI"""
        sei_list = []
        
        if len(video_data) < 2:
            return sei_list
        
        # FLV视频数据格式
        frame_type = (video_data[0] & 0xF0) >> 4
        codec_id = video_data[0] & 0x0F
        
        # 检查是否是AVC (H.264)
        if codec_id == 7:  # AVC
            if len(video_data) < 5:
                return sei_list
                
            avc_packet_type = video_data[1]
            composition_time = struct.unpack('>I', b'\x00' + video_data[2:5])[0]
            
            if avc_packet_type == 0:  # AVC sequence header
                # 解析AVC decoder configuration record
                pass
            elif avc_packet_type == 1:  # AVC NALU
                nalu_data = video_data[5:]
                sei_list.extend(self._parse_h264_nalus(nalu_data))
        
        return sei_list
    
    def _parse_h264_nalus(self, data: bytes) -> List[Dict[str, Any]]:
        """解析H.264 NALU数据"""
        sei_list = []
        offset = 0
        
        while offset < len(data):
            if offset + 4 > len(data):
                break
            
            # 读取NALU长度 (网络字节序)
            nalu_length = struct.unpack('>I', data[offset:offset+4])[0]
            offset += 4
            
            if offset + nalu_length > len(data):
                break
            
            nalu_data = data[offset:offset+nalu_length]
            if len(nalu_data) > 0:
                nalu_type = nalu_data[0] & 0x1F
                
                # SEI NALU type = 6
                if nalu_type == 6:
                    sei_payloads = self._parse_sei_nalu(nalu_data)
                    sei_list.extend(sei_payloads)
            
            offset += nalu_length
        
        return sei_list
    
    def _parse_h264_stream(self, data: bytes) -> List[Dict[str, Any]]:
        """解析H.264裸流"""
        sei_list = []
        
        # 查找起始码 0x000001 或 0x00000001
        start_codes = [b'\x00\x00\x01', b'\x00\x00\x00\x01']
        offset = 0
        
        while offset < len(data):
            # 查找下一个起始码
            next_start = len(data)
            start_code_len = 0
            
            for sc in start_codes:
                pos = data.find(sc, offset)
                if pos != -1 and pos < next_start:
                    next_start = pos
                    start_code_len = len(sc)
            
            if next_start == len(data):
                break
            
            # 查找这个NALU的结束位置
            nalu_start = next_start + start_code_len
            nalu_end = len(data)
            
            for sc in start_codes:
                pos = data.find(sc, nalu_start)
                if pos != -1 and pos < nalu_end:
                    nalu_end = pos
            
            if nalu_start < nalu_end:
                nalu_data = data[nalu_start:nalu_end]
                if len(nalu_data) > 0:
                    nalu_type = nalu_data[0] & 0x1F
                    
                    # SEI NALU type = 6
                    if nalu_type == 6:
                        sei_payloads = self._parse_sei_nalu(nalu_data)
                        sei_list.extend(sei_payloads)
            
            offset = next_start + start_code_len
        
        return sei_list
    
    def _parse_h265_stream(self, data: bytes) -> List[Dict[str, Any]]:
        """解析H.265裸流"""
        sei_list = []
        
        # 查找起始码
        start_codes = [b'\x00\x00\x01', b'\x00\x00\x00\x01']
        offset = 0
        
        while offset < len(data):
            # 查找下一个起始码
            next_start = len(data)
            start_code_len = 0
            
            for sc in start_codes:
                pos = data.find(sc, offset)
                if pos != -1 and pos < next_start:
                    next_start = pos
                    start_code_len = len(sc)
            
            if next_start == len(data):
                break
            
            # 查找这个NALU的结束位置
            nalu_start = next_start + start_code_len
            nalu_end = len(data)
            
            for sc in start_codes:
                pos = data.find(sc, nalu_start)
                if pos != -1 and pos < nalu_end:
                    nalu_end = pos
            
            if nalu_start < nalu_end:
                nalu_data = data[nalu_start:nalu_end]
                if len(nalu_data) >= 2:
                    nalu_type = (nalu_data[0] >> 1) & 0x3F
                    
                    # H.265 SEI NALU types: 39 (PREFIX_SEI) and 40 (SUFFIX_SEI)
                    if nalu_type in [39, 40]:
                        sei_payloads = self._parse_sei_nalu(nalu_data, is_h265=True)
                        sei_list.extend(sei_payloads)
            
            offset = next_start + start_code_len
        
        return sei_list
    
    def _parse_mp4(self, data: bytes) -> List[Dict[str, Any]]:
        """解析MP4文件"""
        # 简化的MP4解析，主要查找mdat box中的视频数据
        sei_list = []
        offset = 0
        
        while offset < len(data) - 8:
            box_size = struct.unpack('>I', data[offset:offset+4])[0]
            box_type = data[offset+4:offset+8]
            
            if box_size == 0:
                box_size = len(data) - offset
            elif box_size == 1:
                if offset + 16 > len(data):
                    break
                box_size = struct.unpack('>Q', data[offset+8:offset+16])[0]
                box_data_start = offset + 16
            else:
                box_data_start = offset + 8
            
            if box_type == b'mdat':
                # 在mdat中查找H.264/H.265数据
                mdat_data = data[box_data_start:offset+box_size]
                # 尝试解析为H.264
                try:
                    sei_list.extend(self._parse_h264_nalus(mdat_data))
                except:
                    pass
                # 尝试解析为H.265
                try:
                    sei_list.extend(self._parse_h265_stream(mdat_data))
                except:
                    pass
            
            offset += box_size
        
        return sei_list
    
    def _auto_detect_and_parse(self, data: bytes) -> List[Dict[str, Any]]:
        """自动检测文件格式并解析"""
        sei_list = []
        
        # 尝试不同的解析方法
        try:
            sei_list.extend(self._parse_h264_stream(data))
        except:
            pass
        
        try:
            sei_list.extend(self._parse_h265_stream(data))
        except:
            pass
        
        return sei_list
    
    def _parse_sei_nalu(self, nalu_data: bytes, is_h265: bool = False) -> List[Dict[str, Any]]:
        """解析SEI NALU"""
        sei_list = []
        
        if is_h265:
            # H.265 NALU头是2字节
            if len(nalu_data) < 3:
                return sei_list
            payload_start = 2
        else:
            # H.264 NALU头是1字节
            if len(nalu_data) < 2:
                return sei_list
            payload_start = 1
        
        offset = payload_start
        
        while offset < len(nalu_data):
            # 解析SEI payload type
            sei_type = 0
            while offset < len(nalu_data) and nalu_data[offset] == 0xFF:
                sei_type += 255
                offset += 1
            
            if offset >= len(nalu_data):
                break
            
            sei_type += nalu_data[offset]
            offset += 1
            
            # 解析SEI payload size
            sei_size = 0
            while offset < len(nalu_data) and nalu_data[offset] == 0xFF:
                sei_size += 255
                offset += 1
            
            if offset >= len(nalu_data):
                break
            
            sei_size += nalu_data[offset]
            offset += 1
            
            # 读取SEI payload数据
            if offset + sei_size > len(nalu_data):
                sei_size = len(nalu_data) - offset
            
            sei_payload = nalu_data[offset:offset+sei_size]
            
            sei_info = {
                'sei_type': sei_type,
                'sei_type_name': self.sei_types.get(sei_type, f'unknown_{sei_type}'),
                'size': sei_size,
                'payload_hex': sei_payload.hex(),
                'payload_bytes': sei_payload,
                'codec': 'H.265' if is_h265 else 'H.264'
            }
            
            # 尝试解析为字符串
            try:
                # 移除尾部的0x00字节
                clean_payload = sei_payload.rstrip(b'\x00')
                sei_info['payload_string'] = clean_payload.decode('utf-8', errors='ignore')
                
                # 尝试解析为JSON
                try:
                    sei_info['payload_json'] = json.loads(sei_info['payload_string'])
                except:
                    pass
            except:
                sei_info['payload_string'] = None
            
            sei_list.append(sei_info)
            offset += sei_size
        
        return sei_list
    
    def print_sei_info(self, sei_list: List[Dict[str, Any]]):
        """打印SEI信息"""
        if not sei_list:
            print("未找到SEI数据")
            return
        
        print(f"找到 {len(sei_list)} 个SEI payload:")
        print("=" * 80)
        
        for i, sei in enumerate(sei_list, 1):
            print(f"\nSEI #{i}:")
            print(f"  编解码器: {sei['codec']}")
            print(f"  SEI类型: {sei['sei_type']} ({sei['sei_type_name']})")
            print(f"  数据大小: {sei['size']} 字节")
            print(f"  16进制数据: {sei['payload_hex']}")
            
            if sei['payload_string']:
                print(f"  字符串内容: {repr(sei['payload_string'])}")
                
                if 'payload_json' in sei:
                    print(f"  JSON内容: {json.dumps(sei['payload_json'], indent=2, ensure_ascii=False)}")
            
            print("-" * 40)


def main():
    if len(sys.argv) != 2:
        print("用法: python sei_parser.py <文件路径>")
        print("支持的文件格式: .flv, .mp4, .h264, .h265, .265, .hevc")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    try:
        parser = SEIParser()
        sei_list = parser.parse_file(filepath)
        parser.print_sei_info(sei_list)
    except Exception as e:
        print(f"解析错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()