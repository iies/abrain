#!/bin/bash
# 오늘 날씨와 미세먼지를 한글 몇 줄로 출력한다. 키가 필요 없는 Open-Meteo를 쓴다. 읽기만 한다.
#
#   weather.sh              서울
#   weather.sh 판교         아래 표에 있는 지역 이름
#   weather.sh 37.39,127.11 위도,경도
#   weather.sh Tokyo        표에 없으면 Open-Meteo 지명 검색 (영문 이름이 정확하다)
#   weather.sh --json 판교  같은 내용을 JSON 한 줄로 (morning-report.py 의 weather 값으로 쓴다)
#
# 실패하면 이유를 한 줄 출력하고 종료 코드 1로 끝난다. 값을 지어내지 않는다.

set -uo pipefail

FORMAT="text"
if [ "${1:-}" = "--json" ]; then FORMAT="json"; shift; fi
PLACE="${1:-서울}"
UA="abrain-morning"

fetch() { curl -sS -m 15 -A "$UA" -G "$@"; }

coords() {
  case "$1" in
    서울|서울시|서울특별시|종로|광화문|시청|을지로) echo "37.5665,126.9780" ;;
    강남|강남구|역삼|삼성|선릉|테헤란로)           echo "37.4979,127.0276" ;;
    서초|서초구|양재)                             echo "37.4837,127.0324" ;;
    여의도|영등포)                                echo "37.5219,126.9245" ;;
    마포|홍대|상암)                               echo "37.5663,126.9014" ;;
    성수|성동|성동구)                             echo "37.5446,127.0559" ;;
    구로|가산|가산디지털단지|금천)                echo "37.4812,126.8827" ;;
    잠실|송파|송파구)                             echo "37.5133,127.1001" ;;
    판교|판교역)                                  echo "37.3948,127.1112" ;;
    분당|분당구|정자|서현)                        echo "37.3828,127.1189" ;;
    성남|성남시)                                  echo "37.4201,127.1265" ;;
    수원|수원시|광교)                             echo "37.2636,127.0286" ;;
    용인|용인시)                                  echo "37.2411,127.1776" ;;
    인천|인천시|송도)                             echo "37.4563,126.7052" ;;
    대전|대전시)                                  echo "36.3504,127.3845" ;;
    세종|세종시)                                  echo "36.4800,127.2890" ;;
    대구|대구시)                                  echo "35.8714,128.6014" ;;
    부산|부산시)                                  echo "35.1796,129.0756" ;;
    울산|울산시)                                  echo "35.5384,129.3114" ;;
    광주|광주시|광주광역시)                       echo "35.1595,126.8526" ;;
    제주|제주시)                                  echo "33.4996,126.5312" ;;
    *) return 1 ;;
  esac
}

LABEL="$PLACE"
if printf '%s' "$PLACE" | grep -Eq '^-?[0-9]+(\.[0-9]+)?,-?[0-9]+(\.[0-9]+)?$'; then
  LL="$PLACE"
elif LL="$(coords "$PLACE")"; then
  :
else
  GEO="$(fetch 'https://geocoding-api.open-meteo.com/v1/search' --data-urlencode "name=$PLACE" -d count=1 -d language=ko)" || {
    echo "날씨 실패: 지명 검색 요청 실패 ($PLACE)"; exit 1; }
  PARSED="$(printf '%s' "$GEO" | python3 -c '
import json, sys
try:
    r = json.load(sys.stdin)["results"][0]
except Exception:
    sys.exit(1)
print("%s,%s" % (r["latitude"], r["longitude"]))
print(", ".join(x for x in (r.get("name"), r.get("admin1"), r.get("country")) if x))
')" || { echo "날씨 실패: \"$PLACE\"의 위치를 찾지 못했습니다. 위도,경도로 지정하거나 영문 지명을 써 주세요."; exit 1; }
  LL="$(printf '%s\n' "$PARSED" | sed -n 1p)"
  LABEL="$PLACE → $(printf '%s\n' "$PARSED" | sed -n 2p) (지명 검색 결과, 다르면 위도,경도로 지정)"
fi

LAT="${LL%,*}"; LON="${LL#*,}"

WX="$(fetch 'https://api.open-meteo.com/v1/forecast' -d "latitude=$LAT" -d "longitude=$LON" \
  -d 'current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m' \
  -d 'hourly=temperature_2m,precipitation_probability,weather_code' \
  -d 'daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,sunset' \
  -d 'timezone=auto' -d 'forecast_days=2' -d 'past_days=1')" || { echo "날씨 실패: 예보 요청 실패"; exit 1; }

# 미세먼지는 실패해도 날씨는 출력한다.
AIR="$(fetch 'https://air-quality-api.open-meteo.com/v1/air-quality' -d "latitude=$LAT" -d "longitude=$LON" \
  -d 'current=pm10,pm2_5' -d 'timezone=auto' 2>/dev/null)" || AIR=""

WX="$WX" AIR="$AIR" LABEL="$LABEL" LL="$LL" FORMAT="$FORMAT" python3 - <<'PY'
import json, os, sys

CODES = {
    0: "맑음", 1: "대체로 맑음", 2: "구름 조금", 3: "흐림", 45: "안개", 48: "서리 안개",
    51: "약한 이슬비", 53: "이슬비", 55: "강한 이슬비", 56: "어는 이슬비", 57: "강한 어는 이슬비",
    61: "약한 비", 63: "비", 65: "강한 비", 66: "어는 비", 67: "강한 어는 비",
    71: "약한 눈", 73: "눈", 75: "강한 눈", 77: "싸락눈",
    80: "약한 소나기", 81: "소나기", 82: "강한 소나기", 85: "약한 눈 소나기", 86: "강한 눈 소나기",
    95: "뇌우", 96: "우박 동반 뇌우", 99: "강한 우박 동반 뇌우",
}
SNOW = {71, 73, 75, 77, 85, 86}


def sky(code):
    return CODES.get(code, f"날씨 코드 {code}")


def grade(v, cuts):  # 한국 환경부 예보 등급
    for limit, name in cuts:
        if v <= limit:
            return name
    return "매우 나쁨"


try:
    wx = json.loads(os.environ["WX"])
    cur, daily, hourly = wx["current"], wx["daily"], wx["hourly"]
except Exception as e:
    body = os.environ.get("WX", "")[:200]
    print(f"날씨 실패: 예보 응답을 읽지 못했습니다 ({e}) {body}")
    sys.exit(1)

today = cur["time"][:10]
try:
    i = daily["time"].index(today)
except ValueError:
    print(f"날씨 실패: 응답에 오늘({today}) 예보가 없습니다")
    sys.exit(1)

tmax, tmin = daily["temperature_2m_max"][i], daily["temperature_2m_min"][i]
pop = daily["precipitation_probability_max"][i]
rain = daily["precipitation_sum"][i]
code = daily["weather_code"][i]

out = []
print = out.append  # 아래 줄들을 모았다가 형식에 맞춰 낸다
print(f"날씨 — {os.environ['LABEL']} ({os.environ['LL']}) · {cur['time'].replace('T', ' ')} 기준 · 출처 Open-Meteo")
print(f"현재: {cur['temperature_2m']}°C (체감 {cur['apparent_temperature']}°C), {sky(cur['weather_code'])}, "
      f"습도 {cur['relative_humidity_2m']}%, 바람 {cur['wind_speed_10m']}km/h")

line = f"오늘: {sky(code)}, 최저 {tmin}°C / 최고 {tmax}°C"
if i > 0 and daily["temperature_2m_max"][i - 1] is not None:
    diff = round(tmax - daily["temperature_2m_max"][i - 1], 1)
    line += f" (어제 최고보다 {diff:+}°C)"
line += f", 강수확률 최대 {pop}%, 예상 강수량 {rain}mm, 일몰 {daily['sunset'][i][11:]}"
print(line)

slots, hours = [], []
for t, temp, p, c in zip(hourly["time"], hourly["temperature_2m"], hourly["precipitation_probability"], hourly["weather_code"]):
    if t[:10] == today and t[11:13] in ("09", "12", "15", "18", "21"):
        slots.append(f"{t[11:13]}시 {temp}°C {sky(c)} {p}%")
        hours.append({"hour": t[11:13], "temp": temp, "sky": sky(c), "pop": p})
if slots:
    print("시간대(기온·하늘·강수확률): " + " | ".join(slots))

pm25 = None
dust = ""
try:
    air = json.loads(os.environ.get("AIR") or "{}")["current"]
    pm10, pm25 = air["pm10"], air["pm2_5"]
    dust = (f"미세먼지 {grade(pm10, [(30, '좋음'), (80, '보통'), (150, '나쁨')])} · "
            f"초미세먼지 {grade(pm25, [(15, '좋음'), (35, '보통'), (75, '나쁨')])}")
    print(f"미세먼지: PM10 {pm10:.0f}㎍/㎥ ({grade(pm10, [(30, '좋음'), (80, '보통'), (150, '나쁨')])}) · "
          f"PM2.5 {pm25:.0f}㎍/㎥ ({grade(pm25, [(15, '좋음'), (35, '보통'), (75, '나쁨')])}) · {air['time'].replace('T', ' ')} 기준")
except Exception:
    print("미세먼지: 가져오지 못함")

if i + 1 < len(daily["time"]):
    j = i + 1
    print(f"내일: {sky(daily['weather_code'][j])}, 최저 {daily['temperature_2m_min'][j]}°C / 최고 {daily['temperature_2m_max'][j]}°C, "
          f"강수확률 최대 {daily['precipitation_probability_max'][j]}%")

tomorrow = ""
if i + 1 < len(daily["time"]):
    tomorrow = (f"{sky(daily['weather_code'][i + 1])}, {daily['temperature_2m_min'][i + 1]} / "
                f"{daily['temperature_2m_max'][i + 1]}°C, 강수확률 {daily['precipitation_probability_max'][i + 1]}%")

tips = []
wet = "눈" if code in SNOW else "비"
if pop is not None and pop >= 60:
    tips.append(f"{wet} 올 가능성이 높습니다 — 우산을 챙기세요")
elif pop is not None and pop >= 30:
    tips.append(f"{wet} 올 수 있습니다 — 접이식 우산")
else:
    tips.append("우산은 필요 없어 보입니다")
if tmax - tmin >= 10:
    tips.append(f"일교차 {round(tmax - tmin, 1)}°C — 겉옷")
if tmin <= 0:
    tips.append("아침 기온이 영하입니다 — 빙판 주의")
if tmax >= 33:
    tips.append("폭염 수준입니다 — 한낮 외출 주의")
if pm25 is not None and pm25 > 35:
    tips.append("초미세먼지 나쁨 — 마스크")
print("한 줄: " + ". ".join(tips) + ".")

import builtins
if os.environ.get("FORMAT") == "json":
    builtins.print(json.dumps({
        "place": os.environ["LABEL"].split(" → ")[0],
        "asof": cur["time"].replace("T", " "),
        "now": f"{cur['temperature_2m']}°C",
        "sky": sky(cur["weather_code"]),
        "feels": f"{cur['apparent_temperature']}°C",
        "low": tmin, "high": tmax,
        "rain": f"{pop}%",
        "dust": dust,
        "tomorrow": tomorrow,
        "tip": ". ".join(tips) + ".",
        "hours": hours,
    }, ensure_ascii=False))
else:
    builtins.print("\n".join(out))
PY
