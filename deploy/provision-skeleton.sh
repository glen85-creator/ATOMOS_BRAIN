#!/usr/bin/env bash
# 조직 골격: 미생성 7슬롯을 paused 스텁으로 생성. create(201,idle) → PATCH(status paused + id기반 instructions 경로).
# 멱등(동명 존재 시 create skip, patch는 재적용 무해). 순서: BRAND_DIVISION → (uuid sed) CONTENTS → 나머지.
# VPS 호스트 실행. 사전: deploy/ rsync(payloads/skeleton·uuid-map.env 포함).
set -uo pipefail
cd "$(dirname "$0")"
source ./uuid-map.env
PC="${PC:-paperclip-sab7-paperclip-1}"
CID="$COMPANY_ID"
API="http://localhost:3100"

login(){ docker exec -u node "$PC" bash -lc 'curl -s -c /tmp/pc.cookies -o /dev/null -X POST http://localhost:3100/api/auth/sign-in/email -H "Content-Type: application/json" -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"'; }

agent_id(){ # $1=name → id(or empty)
  docker exec -u node "$PC" bash -lc "curl -s -b /tmp/pc.cookies $API/api/companies/$CID/agents" \
   | python3 -c "import sys,json;a=json.load(sys.stdin);a=a if isinstance(a,list) else a.get('agents',[]);print(next((x['id'] for x in a if x.get('name')=='$1'),''))"
}

create(){ # stdin=payload → new id
  cat | docker exec -i -u node "$PC" bash -lc "curl -s -b /tmp/pc.cookies -X POST $API/api/companies/$CID/agents -H 'Content-Type: application/json' -H 'Origin: $API' --data-binary @-" \
   | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('id',''))
except Exception: print('')"
}

model_of(){ python3 -c "import json;print(json.load(open('$1'))['adapterConfig']['model'])"; }

patch_stub(){ # $1=id $2=model → http code
  python3 -c "
import json
print(json.dumps({'status':'paused','adapterConfig':{'model':'$2','provider':'openrouter','toolsets':'terminal','timeoutSec':600,'hermesCommand':'/paperclip/.local/bin/hermes','persistSession':True,'instructionsEntryFile':'AGENTS.md','instructionsBundleMode':'managed','instructionsFilePath':'/paperclip/instances/default/companies/$CID/agents/$1/instructions/AGENTS.md','instructionsRootPath':'/paperclip/instances/default/companies/$CID/agents/$1/instructions'}}))" \
   | docker exec -i -u node "$PC" bash -lc "curl -s -o /dev/null -w '%{http_code}' -b /tmp/pc.cookies -X PATCH $API/api/agents/$1 -H 'Content-Type: application/json' -H 'Origin: $API' --data-binary @-"
}

provision(){ # $1=name $2=payloadfile
  local id; id=$(agent_id "$1")
  if [ -n "$id" ]; then echo "$1=$id (exists — skip create)"; else
    id=$(create < "$2")
    if [ -z "$id" ]; then echo "$1 CREATE FAILED (see payload $2)"; return 1; fi
    echo "$1=$id (created)"
  fi
  local m code; m=$(model_of "$2"); code=$(patch_stub "$id" "$m")
  echo "   patch(status=paused+instr,model=$m): HTTP=$code"
  echo "$1=$id" >> /tmp/skel_uuids.env
}

login
: > /tmp/skel_uuids.env

# 1) BRAND_DIVISION 먼저(CONTENTS reportsTo 의존)
provision ATOMOS_BRAND_DIVISION payloads/skeleton/BRAND_DIVISION.json
BD=$(agent_id ATOMOS_BRAND_DIVISION)
if [ -z "$BD" ]; then echo "FATAL: BRAND_DIVISION uuid 없음 — CONTENTS 중단"; else
  sed "s/__BRAND_DIVISION_UUID__/$BD/" payloads/skeleton/CONTENTS_STUDIO.json > /tmp/contents_skel.json
  provision ATOMOS_CONTENTS_STUDIO /tmp/contents_skel.json
fi

# 2) 나머지(CEO/CTO 기존 uuid 참조). SCM은 Task1서 생성됨 → skip create + 재patch(무해).
for S in SCM_TEAM FINANCE_TEAM CRM_TEAM ARCHIVES_TEAM VISION_AI_TEAM; do
  provision "ATOMOS_$S" "payloads/skeleton/$S.json"
done

echo "=== 생성 uuid 매핑 ==="; cat /tmp/skel_uuids.env
echo "=== 전체 에이전트 ==="
docker exec -u node "$PC" bash -lc "curl -s -b /tmp/pc.cookies $API/api/companies/$CID/agents" \
 | python3 -c "import sys,json;a=json.load(sys.stdin);a=a if isinstance(a,list) else a.get('agents',[]);print('total',len(a));[print('  ',x['name'],'|',x['status'],'|',str(x.get('reportsTo'))[:8]) for x in sorted(a,key=lambda y:y.get('name',''))]"
