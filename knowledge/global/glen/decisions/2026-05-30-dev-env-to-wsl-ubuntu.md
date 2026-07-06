---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 개발 주 환경을 Windows(D드라이브)에서 WSL/우분투로 이전"
tags: [domain/devops, status/accepted, glen-wiki, type/decision]
---
# ADR: 개발 주 환경을 Windows(D드라이브)에서 WSL/우분투로 이전

## 컨텍스트

[[global/glen/entities-projects/HBS-Dashboard]]·[[global/glen/entities-projects/HBS-FastAPI]]를 그동안 Windows `D:\WORK\HBS\` 에서 개발해 왔다. 같은 GitHub 리포가 우분투(WSL) `/home/glen_85/` 에도 클론되면서 **같은 리포가 두 곳에 존재**하게 됐고, 다음 혼란이 발생:

- **줄바꿈 오염**: D드라이브(Windows) 작업트리가 CRLF로 받아져 `git status`에 100~125개 파일이 "변경됨"으로 뜸 (실제 내용 변경은 3개뿐, 나머지는 줄바꿈만 뒤집힌 가짜 diff).
- **/mnt/d 성능**: WSL에서 Windows 드라이브(`/mnt/d`)는 파일 I/O가 매우 느림.
- **자동 적재 단절**: [[global/glen/entities-projects/GLEN_WORK]]의 `auto_ingest.py`(Stop 훅)가 Windows 경로로 하드코딩돼 있어, 우분투 세션의 작업이 세컨드 브레인에 적재되지 않음.

## 결정

**우분투(WSL)를 주 작업 환경으로 삼고, D드라이브 클론은 백업/`git pull` 전용으로 강등한다.**

- 주 작업 폴더: `/home/glen_85/hbs-dashboard`, `/home/glen_85/FastAPI` (FastAPI는 이날 우분투로 신규 클론, 활성 브랜치 `feature/master-rework`).
- `.gitattributes`에 `* text=auto eol=lf` 추가 → 줄바꿈 LF 고정으로 CRLF 대량 diff 영구 차단 (두 리포 모두).
- WSL에는 gh CLI·토큰이 없어, 푸시는 Windows Git 자격증명관리자(GCM)를 빌려 씀:
  `credential.helper = !"/mnt/c/Program Files/Git/mingw64/bin/git-credential-manager.exe"`.
- git identity(global): `glen <glen_85@hbscom.com>`.
- `auto_ingest.py`를 OS 인식형으로 패치 (`sys.platform` 분기) — WSL에서는 소스=우분투 클론, 메모리=`/home/glen_85/.claude/projects/-home-glen-85-hbs-dashboard/memory` 사용. 프로젝트 Stop 훅 명령을 `python3 /mnt/d/WORK/GLEN/GLEN_WORK/scripts/auto_ingest.py`로 교체.

## 결과

**긍정**: 단일 작업 환경으로 혼란 제거. 빌드·git 속도 향상. 줄바꿈 재발 차단. 우분투 세션 작업이 세컨드 브레인에 자동 적재 재개 (미러로 검증 완료).

**부정/주의**: 볼트(GLEN_WORK) 자체는 여전히 D드라이브에만 존재 → WSL에서 `/mnt/d`로 쓰기(느리지만 간헐적이라 허용). 두 환경에서 동시에 같은 리포를 편집하면 다시 갈라질 수 있으므로 **D드라이브는 절대 직접 편집 금지, pull 전용** 원칙 유지 필요.

## 대안 검토

- **A. 우분투 주 환경 (채택)** — 성능·일관성 최적.
- **B. D드라이브 유지 + WSL 폐기** — /mnt/d 성능 문제와 CRLF 오염이 남아 기각.
- **C. 양쪽 병행** — 이번 혼란의 원인. 기각.

## 참고

- 줄바꿈 가짜 diff는 `git diff -w`(공백 무시)로 진짜 변경만 식별해 폐기(`git restore .`).
- 커밋: dashboard `e122513`(.gitattributes/.gitignore), FastAPI `a992599`(.gitattributes).

## 관련

- [[global/glen/entities-projects/HBS-Dashboard]]
- [[global/glen/entities-projects/HBS-FastAPI]]
- [[global/glen/entities-projects/GLEN_WORK]]
- [[global/glen/entities-people/glen]]

## 출처(원본)

- raw/docs/hbs-dashboard/memory/repo-clones-and-git-setup
