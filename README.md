# 2026 UROP — GTX-A 광역버스 수요 분석

GTX-A 개통 전·후 경기 북부 광역버스 이용량을 비교하고, GTX-A와 경합할 가능성이 있는 광역버스 노선을 구축하기 위한 연구 코드 저장소입니다.

## 연구 대상

GTX-A 북측 역과 연계된 다음 지역의 서울행 광역버스를 대상으로 합니다.

- 운정중앙역 — 파주시
- 킨텍스역 — 고양시 일산서구
- 대곡역 — 고양시 덕양구

노선 후보는 경기도 전체 버스 노선에서 광역버스 유형을 선별한 뒤, 대상지역 정류장을 통과하고 서울특별시 정류장이 있는 노선을 추출하는 방식으로 구축했습니다.

## 작업 흐름

```text
경기도 버스 노선·정류장 정보 조회
        ↓
GTX-A 대상지역 및 서울행 광역버스 후보 추출
        ↓
STCIS 노선번호로 노선 ID 확인
        ↓
교통카드 합성데이터 API 조회
        ↓
노선별 이용량 및 수요 변화 분석
```

## 파일 구성

| 파일 | 설명 |
|---|---|
| `Desktop/Gachon/3-2/UROP/01_gtx_a_route_selection.py` | GTX-A 대상지역의 서울행 광역버스 후보 추출 |
| `Desktop/Gachon/3-2/UROP/01_gtx_a_route_selection.ipynb` | 노선 후보 추출 과정 확인용 노트북 |
| `Desktop/Gachon/3-2/UROP/02_stcis_route_id_lookup.ipynb` | 버스번호별 STCIS 노선 ID·기점·종점 조회 |
| `Desktop/Gachon/3-2/UROP/03_gtx_transport_card_api_20241017.ipynb` | 2024년 10월 17일 교통카드 합성데이터 API 조회 |
| `Desktop/Gachon/3-2/UROP/gtx_a_seoul_bus_outputs/` | 노선 후보 및 요약 CSV |

## 실행 순서

1. `01_gtx_a_route_selection.py` 또는 노트북을 실행해 노선 후보 CSV를 생성합니다.
2. `02_stcis_route_id_lookup.ipynb`에서 STCIS API 키를 입력하고 버스번호별 노선 ID를 확인합니다.
3. `03_gtx_transport_card_api_20241017.ipynb`에서 공공데이터포털 API 키를 입력하고 교통카드 이용자료를 조회합니다.

## API 키

API 키는 코드에 직접 입력하지 않고 `.env` 파일 또는 노트북의 입력란을 사용합니다. `.env` 파일은 Git에 업로드되지 않도록 `.gitignore`에 등록되어 있습니다.

필요한 API는 다음과 같습니다.

- 경기도 버스 노선·정류장 정보 API
- STCIS 노선기반정보 API
- 경기도 교통카드 이용내역 합성데이터 API

## 참고

교통카드 이용내역 합성데이터는 실제 이용 패턴을 기반으로 생성된 합성데이터이며, 개인 식별을 위한 자료가 아닙니다.
