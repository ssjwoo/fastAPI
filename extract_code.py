#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# temp.py에서 순수 Python 코드만 추출하는 스크립트

with open('temp.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 22번째 줄부터 780번째 줄까지 추출 (인덱스는 0부터 시작하므로 21~779)
python_code_lines = lines[21:780]

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(python_code_lines)

print("main.py 파일이 생성되었습니다.")