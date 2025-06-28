import sys
import json

# ANSI escape codes for colors
class Colors:
    RESET = '\x1b[0m'
    BOLD = '\x1b[1m'
    RED = '\x1b[91m'
    GREEN = '\x1b[92m'
    YELLOW = '\x1b[93m'
    BLUE = '\x1b[94m'
    CYAN = '\x1b[96m'

def print_pretty(message, color=Colors.RESET, bold=False):
    """Prints a message with specified color and boldness."""
    style = Colors.BOLD if bold else ''
    print(f"{style}{color}{message}{Colors.RESET}")

def parse_sei_message(payload):
    """Parses one or more SEI messages from a SEI NALU payload."""
    offset = 0
    while offset < len(payload):
        if payload[offset] == 0x80: # Stop bit
            break

        # 1. Parse SEI Type
        sei_type = 0
        while offset < len(payload) and payload[offset] == 0xFF:
            sei_type += 255
            offset += 1
        if offset < len(payload):
            sei_type += payload[offset]
            offset += 1

        # 2. Parse SEI Size
        sei_size = 0
        while offset < len(payload) and payload[offset] == 0xFF:
            sei_size += 255
            offset += 1
        if offset < len(payload):
            sei_size += payload[offset]
            offset += 1
        
        if offset + sei_size > len(payload):
            print_pretty(f"Warning: Incomplete SEI message. Expected size {sei_size}, but not enough data.", color=Colors.RED)
            break

        # 3. Extract SEI Payload
        sei_payload = payload[offset:offset + sei_size]
        offset += sei_size

        # 4. Print formatted output
        print_pretty("─" * 60, color=Colors.YELLOW)
        print_pretty(f"  SEI Message Found", color=Colors.YELLOW, bold=True)
        type_str = " (User data unregistered)" if sei_type == 5 else ""
        print_pretty(f"    ├─ SEI Type : {sei_type}{type_str}", color=Colors.CYAN)
        print_pretty(f"    ├─ Size     : {sei_size}", color=Colors.CYAN)
        
        try:
            # Clean up trailing null bytes and whitespace which are common in SEI payloads
            str_payload = sei_payload.decode('utf-8').rstrip('\x00').strip()
            
            try:
                # Attempt to parse the string as JSON
                json_obj = json.loads(str_payload)
                # If successful, pretty-print the JSON
                pretty_json = json.dumps(json_obj, indent=4)
                print_pretty(f"    ├─ Payload (JSON) :\n{pretty_json}", color=Colors.GREEN)
            except json.JSONDecodeError:
                # If it fails, treat it as a regular string
                print_pretty(f"    ├─ Payload (String) : {str_payload}", color=Colors.RESET)

        except UnicodeDecodeError:
            print_pretty(f"    ├─ Payload (String) : Not a valid UTF-8 string.", color=Colors.RED)

        print_pretty(f"    └─ Payload (Hex)    : {sei_payload.hex()}", color=Colors.RESET)
        print_pretty("─" * 60, color=Colors.YELLOW)
        print()

def parse_flv(file_path):
    """Parses an FLV file to find and process SEI NALUs."""
    print_pretty(f"Parsing file: {file_path}\n", color=Colors.BOLD)
    try:
        with open(file_path, 'rb') as f:
            header = f.read(9)
            if not header.startswith(b'FLV'):
                print_pretty("Error: Not a valid FLV file.", color=Colors.RED, bold=True)
                return
            
            f.read(4) # Skip PreviousTagSize0

            tag_count = 0
            while True:
                tag_header_data = f.read(11)
                if len(tag_header_data) < 11:
                    break

                tag_type = tag_header_data[0]
                data_size = int.from_bytes(tag_header_data[1:4], 'big')
                
                tag_data = f.read(data_size)
                if len(tag_data) < data_size:
                    break
                
                if tag_type == 9 and len(tag_data) > 5: # Video Tag
                    codec_id = tag_data[0] & 0x0F
                    packet_type = tag_data[1]
                    
                    if codec_id == 7 and packet_type == 1: # H.264 NALUs
                        nalu_offset = 5 # Skip AVCPacket header
                        while nalu_offset + 4 <= len(tag_data):
                            nalu_size = int.from_bytes(tag_data[nalu_offset:nalu_offset+4], 'big')
                            nalu_offset += 4

                            if nalu_offset + nalu_size > len(tag_data):
                                break

                            nalu_data = tag_data[nalu_offset:nalu_offset+nalu_size]
                            nalu_offset += nalu_size
                            
                            if not nalu_data:
                                continue

                            nal_unit_type = nalu_data[0] & 0x1F

                            if nal_unit_type == 6: # SEI
                                parse_sei_message(nalu_data[1:])

                f.read(4) # Skip PreviousTagSize
                tag_count += 1
    except FileNotFoundError:
        print_pretty(f"Error: File not found at {file_path}", color=Colors.RED, bold=True)
    except Exception as e:
        print_pretty(f"An unexpected error occurred: {e}", color=Colors.RED, bold=True)

    print_pretty(f"\nFile parsing complete. Processed {tag_count} tags.", bold=True)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print_pretty("Usage: python3 sei_parser.py <path_to_file>", color=Colors.RED, bold=True)
        sys.exit(1)
    
    file_path = sys.argv[1]
    parse_flv(file_path)
