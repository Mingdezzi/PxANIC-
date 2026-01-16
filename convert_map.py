import json
import sys
from pathlib import Path

TILE_MAPPING = {

    101: 10001,
    102: 10003,
    103: 10002,
    104: 11001,
    106: 10008,
    107: 10010,
    108: 10006,
    109: 10004,


    201: 21001,
    202: 21005,
    203: 21014,
    204: 21006,
    205: 21002,
    502: 21011,


    301: 31301,
    302: 31302,
    303: 31303,
    304: 30001,
    305: 30002,
    306: 30003,
    307: 30099,
    901: 30099,


    401: 51201,
    402: 40101,
    403: 51202,
    404: 51203,
    405: 41003,
    406: 41001,
    501: 51204,


    105: 51306,
    115: 50307,
    125: 50308,
    503: 51301,
    513: 51302,
    505: 51303,
    504: 50304,
    506: 51305,
    520: 51309,
    521: 51310,


    601: 61001,
}

TILE_NAMES = {
    101: "흙 바닥", 102: "자갈길", 103: "잔디", 104: "깊은 물",
    106: "나무 마루", 107: "대리석 바닥", 108: "동굴 바닥", 109: "모래사장",
    201: "붉은 벽돌 벽", 202: "통나무 벽", 203: "동굴 암벽", 204: "하얀 회반죽 벽",
    205: "회색 벽돌 벽", 502: "유리 벽",
    301: "나무 문[닫힘]", 302: "철제 문[닫힘]", 303: "유리 문[닫힘]",
    304: "나무 문[열림]", 305: "철제 문[열림]", 306: "유리 문[열림]",
    307: "부서진 문", 901: "부서진 문",
    401: "나무 상자", 402: "높은 수풀", 403: "캐비닛", 404: "책상",
    405: "거대한 바위", 406: "나무 기둥", 501: "침대",
    105: "빈 밭", 115: "새싹 밭", 125: "다 자란 밭",
    503: "광맥", 513: "채광 잔해", 505: "용광로", 504: "낚시 포인트",
    506: "도마", 520: "현미경", 521: "수술대",
    601: "가로등",
}

def convert_tile_value(value, unknown_tiles):
    """타일 값을 변환하고 알 수 없는 타일을 추적"""
    if isinstance(value, int):
        if value in TILE_MAPPING:
            return TILE_MAPPING[value]
        elif value != 0:
            unknown_tiles.add(value)
        return value
    return value

def convert_map_data(data, unknown_tiles, current_key=None):
    """맵 데이터를 재귀적으로 변환"""
    if isinstance(data, dict):
        return {key: convert_map_data(value, unknown_tiles, key) for key, value in data.items()}
    elif isinstance(data, list):

        if current_key == "zones":
            return data
        return [convert_map_data(item, unknown_tiles, current_key) for item in data]
    else:

        if current_key == "zones":
            return data
        return convert_tile_value(data, unknown_tiles)

def get_user_mapping(old_code):
    """사용자로부터 새 타일 코드 입력받기"""
    print(f"\n알 수 없는 타일 코드 발견: {old_code}")
    while True:
        new_code = input(f"새 타일 코드를 입력하세요 (건너뛰려면 Enter): ").strip()
        if new_code == "":
            return None
        try:
            return int(new_code)
        except ValueError:
            print("올바른 숫자를 입력해주세요.")

def main():
    if len(sys.argv) < 2:
        print("사용법: python tile_converter.py <맵파일.json>")
        print("예시: python tile_converter.py map_data.json")
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(f"오류: 파일을 찾을 수 없습니다 - {input_file}")
        sys.exit(1)


    print(f"맵 파일 로딩 중: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            map_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"오류: JSON 파일 파싱 실패 - {e}")
        sys.exit(1)


    unknown_tiles = set()
    print("타일 코드 변환 중...")
    print("(구역 설정 데이터는 변환하지 않습니다)")
    converted_data = convert_map_data(map_data, unknown_tiles)


    if unknown_tiles:
        print(f"\n{'='*60}")
        print(f"총 {len(unknown_tiles)}개의 알 수 없는 타일 코드가 발견되었습니다.")
        print(f"{'='*60}")

        user_mappings = {}
        for old_code in sorted(unknown_tiles):
            new_code = get_user_mapping(old_code)
            if new_code is not None:
                user_mappings[old_code] = new_code


        if user_mappings:
            print("\n사용자 정의 매핑 적용 중...")
            TILE_MAPPING.update(user_mappings)
            unknown_tiles.clear()
            converted_data = convert_map_data(map_data, unknown_tiles)


    output_file = input_file.parent / f"{input_file.stem}_converted{input_file.suffix}"


    print(f"\n변환된 맵 저장 중: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✓ 변환 완료!")
    print(f"  원본 파일: {input_file}")
    print(f"  변환 파일: {output_file}")
    if unknown_tiles:
        print(f"\n⚠ 주의: {len(unknown_tiles)}개의 타일이 변환되지 않았습니다:")
        for tile in sorted(unknown_tiles):
            print(f"  - 타일 코드: {tile}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()