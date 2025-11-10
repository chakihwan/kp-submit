# 한국폴리텍대학 과제 제출 시스템 (KPU-Submit)


## 📖 프로젝트 소개 (Introduction)

**KPU-Submit**은 기존 Microsoft Teams의 용량 문제로 과제 제출에 불편을 겪는 한국폴리텍대학 학생 및 교직원을 위해 개발된 **Django 기반의 맞춤형 과제 제출 및 관리 시스템**입니다.

이 시스템을 통해 사용자는 누구나 강의나 스터디 그룹에 해당하는 '팀'을 생성하고 관리할 수 있습니다. 팀 생성자는 과제를 출제하고 제출물을 효율적으로 채점할 수 있으며, 팀 참여자는 용량 제한의 스트레스 없이 과제를 제출하고 자신의 성적과 피드백을 체계적으로 관리할 수 있습니다.


## 📸 주요 화면 스크린샷 (Screenshots)

| 로그인 & 회원가입 | 팀 목록 (메인) | 과제 등록 |
| :---: | :---: | :---: |
| ![로그인](https://github.com/user-attachments/assets/a1c71e0f-9399-460b-b04e-b615c4b5629b)|![팀 목록](https://github.com/user-attachments/assets/a7e80369-9bb3-4f84-9365-56d582c80761)|![과제 등록](https://github.com/user-attachments/assets/e9f760fd-37a3-47ca-af27-56d948d5cb78)|
| **과제 제출 페이지** | **제출 현황 및 채점** | **가입 요청 관리** |
|![과제 제출 페이지](https://github.com/user-attachments/assets/1359efb1-d016-4505-90a1-cc82139b2d02)|![제출 현황 및 채점](https://github.com/user-attachments/assets/2365a78b-54e1-4977-8a40-a8cb9bfc3dc9)|![가입 요청 관리](https://github.com/user-attachments/assets/43e8a149-d627-482b-8328-951c6436fe51)|

---

## ✨ 주요 기능 (Features)

### 👨‍🏫 팀 생성자 (Owner)
- **팀 생성 및 관리**: 강의별 '팀'을 생성하고, 설명과 대표 이미지를 등록하여 관리합니다.
- **고유 코드로 멤버 관리**: 팀 참여를 위한 6자리 고유 코드를 생성하고, 불필요할 경우 재발급하여 접근을 제어합니다.
- **가입 요청 승인/거절**: 실제 수강생만 선별하여 가입 요청을 승인하거나 거절할 수 있습니다.
- **유연한 과제 관리**: 과제별로 제목, 설명, 마감일, 배점 등을 설정하고, 필요에 따라 과제를 수동으로 마감하거나 다시 열 수 있습니다.
- **체계적인 채점 시스템**: 학생들의 제출 현황을 한눈에 보고, 제출된 파일을 다운로드하여 확인하며, 점수와 피드백을 남길 수 있습니다.

### 👨‍🎓 팀 참여자 (Member)
- **간편한 회원가입**: 학번, 이름, 이메일만으로 빠르게 가입할 수 있습니다.
- **코드를 통한 팀 참가**: 공유받은 팀 코드를 입력하여 간편하게 가입을 요청하고, 처리 상태를 실시간으로 확인합니다.
- **손쉬운 과제 제출**: 소속된 팀의 과제를 확인하고, 여러 파일을 동시에 첨부하여 제출할 수 있습니다. 마감 전까지는 언제든지 수정 제출이 가능합니다.
- **나의 제출 내역 관리**: 제출 상태(미제출, 제출됨, 채점 완료), 제출 시간, 파일 목록을 한눈에 확인하고, 채점이 완료되면 점수와 피드백을 조회할 수 있습니다.


## 역할 및 핵심 설계
저는 이 프로젝트의 백엔드 시스템 전체를 A-Z까지 설계하고 개발했습니다. 단순히 기능을 구현하는 것을 넘어, 안정성과 효율성을 고려하며 다음과 같은 기술적 결정을 내렸습니다.

- RESTful API 설계: teams/<team_id>/assignments/<assignment_id>/submit처럼, URL만 보고도 데이터의 관계를 파악할 수 있도록 RESTful 엔드포인트를 설계했습니다. (urls.py)

- 안전한 접근 제어 (보안 및 인가): @login_required 데코레이터를 사용해 **인증(Authentication)**을 처리했습니다. 또한, View 함수 내에서 team.owner 혹은 TeamMembership 객체를 직접 조회하여, **'로그인한 사용자가 이 팀의 멤버가 맞는가?'**를 검증하는 인가(Authorization) 로직을 구현해 HttpResponseForbidden(403)으로 안전하게 처리했습니다.

- 효율적인 DB 처리 (ORM 최적화): Submission.objects.get_or_create()를 활용하여, **"기존 제출물이 있으면 가져오고, 없으면 생성하라"**는 복잡한 로G을 단 한 줄의 쿼리로 최적화했습니다.

- 데이터 안정성 및 예외 처리: get_object_or_404()를 적극적으로 활용해, 존재하지 않는 데이터 요청 시 서버가 500 에러를 반환하는 대신 사용자에게 404 페이지를 보여주도록 안정적으로 예외 처리를 했습니다. 또한 POST 요청 처리 후 redirect하는 PRG 패턴을 적용해, 새로고침 시 폼이 중복 제출되는 것을 방지했습니다.

## 프로젝트 회고 및 개선점 (Learned Lessons)
이 프로젝트를 통해 Django의 핵심 기능인 ORM과 View 설계를 깊이 있게 이해할 수 있었습니다. 다만, 파일 업로드 로직(assignment_submit View)에서 '기존 파일 삭제'와 '새 파일 생성'이 분리되어 있어, 만약 새 파일 저장 중 에러가 발생하면 데이터가 꼬일 수 있는 잠재적 위험을 발견했습니다.

[개선 방향] 향후 이 로직 전체를 django.db.transaction.atomic() 블록으로 감싸, 데이터의 원자성(Atomicity)을 보장하여 파일 처리가 100% 성공하거나, 실패할 경우 100% 롤백(취소)되도록 개선할 계획입니다.
---

## 🖥️ 기술 스택 (Tech Stack)

- **Backend**: Python, Django
- **Database**: SQLite
- **Frontend**: HTML, [Tailwind CSS](https://tailwindcss.com/)

---

## 🚀 로컬에서 실행하기 (Getting Started)

### 1. 프로젝트 복제
```bash
git clone [https://github.com/chakihwan/kp-submit.git](https://github.com/chakihwan/kp-submit.git)
cd kp-submit
```

### 2. Python 가상환경 생성 및 활성화
```bash
# Python 3.x 버전이 설치되어 있어야 합니다.
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 필수 패키지 설치
```bash
# 이 프로젝트는 Django 외 별도 패키지가 필요하지 않습니다.
pip install Django
```


### 4. 데이터베이스 마이그레이션
데이터베이스 테이블을 생성합니다.
```bash
python manage.py migrate
```

### 5. 관리자 계정 생성 (선택 사항)
`/admin` 페이지에 접속하기 위한 관리자 계정을 생성합니다.
```bash
python manage.py createsuperuser
```

### 6. 개발 서버 실행
```bash
python manage.py runserver
```
서버가 실행되면, 웹 브라우저에서 `http://127.0.0.1:8000` 주소로 접속하여 확인할 수 있습니다.

---

## 📝 데이터베이스 구조 (ERD)


이 프로젝트의 핵심 모델 관계는 다음과 같습니다.

- **User**: Django의 기본 사용자 모델 (팀 생성자, 참여자 공통)
- **StudentProfile**: User 모델을 확장하여 '학번' 정보 추가 (1:1 관계)
- **Team**: 강의/그룹에 해당하며, `owner`(User)를 가짐
- **TeamMembership**: Team과 User를 연결하여 가입 상태(`status`) 관리 (M:N 관계의 중개 모델)
- **Assignment**: Team에 종속되는 과제 (1:N 관계)
- **Submission**: Assignment에 대한 User의 제출물 (N:1 관계, `uq_assignment_student` 제약조건으로 유일성 보장)
- **SubmissionFile**: Submission에 첨부된 개별 파일 (1:N 관계)
- **Grade**: Submission에 대한 채점 결과 (1:1 관계)

---

## 💡 향후 개선 계획 (Future Work)

- [ ] **실시간 알림 기능**: 과제 마감 임박, 채점 완료, 새 과제 등록 시 사용자에게 알림 전송
- [ ] **대시보드 기능**: 미제출 과제, 마감 임박 과제 등 주요 정보를 요약해서 보여주는 페이지
- [ ] **파일 미리보기**: 제출된 PDF, 이미지, 소스코드 등을 웹에서 바로 확인할 수 있는 기능
- [ ] **전체 관리자 페이지**: 시스템의 모든 팀, 사용자, 과제 현황을 모니터링하는 슈퍼유저용 페이지
