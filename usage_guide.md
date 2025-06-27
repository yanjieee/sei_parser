# SEI解析器使用指南

## 快速开始

### 1. 完整版解析器 (推荐)

```bash
python3 sei_parser.py 22.flv
```

**特点:**
- 支持多种文件格式 (FLV, MP4, H.264, H.265)
- 完整的SEI类型映射
- 详细的错误处理
- 自动格式检测

### 2. 简化版解析器

```bash
python3 simple_sei_parser.py 22.flv
```

**特点:**
- 专门针对FLV文件
- 代码简洁，易于理解
- 快速解析和显示

## 输出解读

### SEI数据结构

每个SEI包含以下信息：

```
SEI #1:
  编解码器: H.264              # 视频编码格式
  SEI类型: 100 (unknown_100)   # SEI类型编号和名称
  数据大小: 372 字节           # payload大小
  16进制数据: 7b0a2020...      # 原始二进制数据
  字符串内容: '{"live_sei...   # 解码后的字符串
  JSON内容: { ... }            # 解析后的JSON对象
```

### 常见SEI类型

从测试文件中发现的SEI类型：

#### SEI类型 100 - 直播元数据
包含直播相关的实时信息：
- `live_sei_mute_mic`: 麦克风状态
- `loudness`: 音频响度信息
- `push_video_height/width`: 推流分辨率
- `real_bitrate`: 实时码率
- `real_video_framerate`: 实时帧率
- `ts`: 时间戳
- `sei_index`: SEI序号

#### SEI类型 101 - 音频响度详情
专业音频测量数据：
- `sourcePeak`: 峰值电平
- `sourceLuft`: LUFS响度
- `sourceIntegrated`: 积分响度
- `sourceMomentary`: 瞬时响度
- `sourceShorterm`: 短期响度


## 扩展开发

### 添加新的SEI类型解析

```python
def parse_custom_sei(payload):
    """解析自定义SEI类型"""
    if payload.startswith(b'CUSTOM'):
        # 自定义解析逻辑
        return {"type": "custom", "data": payload[6:]}
    return None

# 在主解析循环中调用
custom_data = parse_custom_sei(sei_payload)
if custom_data:
    sei_info['custom_parsed'] = custom_data
```

### 输出格式定制

```python
def export_to_csv(sei_list):
    """导出SEI数据到CSV"""
    import csv
    with open('sei_data.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['SEI_Type', 'Size', 'Timestamp', 'Bitrate'])
        
        for sei in sei_list:
            if 'payload_json' in sei:
                data = sei['payload_json']
                writer.writerow([
                    sei['sei_type'],
                    sei['size'],
                    data.get('ts', ''),
                    data.get('real_bitrate', '')
                ])
```

## 性能优化建议

### 1. 大文件处理
```python
def parse_large_file_streaming(filepath):
    """流式处理大文件"""
    chunk_size = 1024 * 1024  # 1MB chunks
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            # 处理chunk中的SEI数据
            process_chunk(chunk)
```

### 2. 内存优化
```python
def parse_sei_minimal(filepath):
    """最小内存占用解析"""
    # 只保存必要的SEI信息
    essential_types = [100, 101]  # 只解析关键类型
    
    for sei in parse_file(filepath):
        if sei['sei_type'] in essential_types:
            yield sei  # 使用生成器减少内存占用
```

## 故障排除

### 常见问题

1. **文件格式不支持**
   - 确认文件扩展名正确
   - 尝试使用自动检测模式

2. **SEI数据为空**
   - 检查文件是否包含视频流
   - 确认编码器是否写入SEI数据

3. **JSON解析失败**
   - SEI数据可能不是JSON格式
   - 检查字符编码问题

4. **性能问题**
   - 使用简化版解析器
   - 考虑流式处理大文件

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查原始数据
print(f"原始SEI数据: {sei_payload.hex()}")
print(f"数据长度: {len(sei_payload)}")

# 验证NALU结构
nalu_type = nalu_data[0] & 0x1F
print(f"NALU类型: {nalu_type}")
```