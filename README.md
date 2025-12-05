# 한국폴리텍대학 과제 제출 시스템 (KPU-Submit)


[![Tech Stack](https://skillicons.dev/icons?i=python,django,sqlite,tailwind,html)](https://skillicons.dev/icons?i=python,django,sqlite,tailwind,html)

## 1. 프로젝트 소개 (Introduction)

**KPU-Submit**은 기존 Microsoft Teams의 용량 문제로 과제 제출에 불편을 겪는 한국폴리텍대학 학생 및 교직원을 위해 개발된 **Python/Django 기반 맞춤형 과제 제출 및 관리 시스템**입니다.

이 시스템을 통해 사용자는 누구나 강의나 스터디 그룹에 해당하는 '팀'을 생성하고 관리할 수 있습니다. 팀 생성자(교수)는 과제를 출제하고 제출물을 효율적으로 채점할 수 있으며, 팀 참여자(학생)는 용량 제한의 스트레스 없이 과제를 제출하고 자신의 성적과 피드백을 체계적으로 관리할 수 있습니다.


## 📸 주요 화면 스크린샷 (Screenshots)

| 로그인 & 회원가입 | 팀 목록 (메인) | 과제 등록 |
| :---: | :---: | :---: |
| ![로그인](https://github.com/user-attachments/assets/a1c71e0f-9399-460b-b04e-b615c4b5629b)|![팀 목록](<img width="1920" height="1040" alt="Image" src="https://github.com/user-attachments/assets/9b0b8017-0ef4-401c-89fa-45f9ff5f30ec" />)|![과제 등록](https://github.com/user-attachments/assets/e9f760fd-37a3-47ca-af27-56d948d5cb78)|
| **과제 제출 페이지** | **제출 현황 및 채점** | **가입 요청 관리** |
|![과제 제출 페이지](https://github.com/user-attachments/assets/1359efb1-d016-4505-90a1-cc82139b2d02)|![제출 현황 및 채점](https://github.com/user-attachments/assets/2365a78b-54e1-4977-8a40-a8cb9bfc3dc9)|![가입 요청 관리](https://github.com/user-attachments/assets/43e8a149-d627-482b-8328-951c6436fe51)|

---

## 2. 주요 기능 (Features)

### 👨‍🏫 팀 생성자 (Owner)
* **팀 생성 및 관리:** 강의별 '팀'을 생성하고, 설명과 대표 이미지를 등록하여 관리합니다.
* **고유 코드로 멤버 관리:** 팀 참여를 위한 6자리 고유 코드를 생성하고, `regen_team_code` 뷰를 통해 재발급하여 접근을 제어합니다.
* **가입 요청 승인/거절:** `TeamMembership` 모델의 상태(`PENDING`, `APPROVED`)를 변경하여, 실제 수강생만 선별적으로 가입을 승인하거나 거절할 수 있습니다.
* **유연한 과제 관리:** 과제별로 마감일, 배점 등을 설정하고, `is_closed` 필드를 통해 필요에 따라 과제를 수동으로 마감하거나 다시 열 수 있습니다.
* **체계적인 채점 시스템:** 학생들의 제출 현황을 한눈에 보고, 제출된 파일을 다운로드하며, `Grade` 모델을 통해 점수와 피드백을 남길 수 있습니다.

### 👨‍🎓 팀 참여자 (Member)
* **안전한 회원가입:** 학번(`student_id`)을 포함한 커스텀 회원가입 로직을 구현했으며, `transaction.atomic`을 통해 User와 StudentProfile이 동시에 생성되도록 데이터 무결성을 보장합니다.
* **코드를 통한 팀 참가:** 6자리 팀 코드를 입력하여 간편하게 가입을 요청하고, 처리 상태(`PENDING`, `APPROVED` 등)를 실시간으로 확인합니다.
* **다중 파일 제출:** `SubmissionFile` 모델(1:N 관계)을 통해, 하나의 과제에 **여러 개의 파일을 동시에 첨부**하여 제출할 수 있습니다.
* **수정 제출:** 과제가 마감되기 전까지는 언제든지 코멘트와 첨부파일을 **덮어쓰는 방식(Update)**으로 수정 제출이 가능합니다.
* **제출 내역 및 성적 확인:** 제출 상태, 시간, 파일 목록을 한눈에 확인하고, 채점이 완료되면 `Grade` 모델에 저장된 점수와 피드백을 조회할 수 있습니다.


## 3. 핵심 설계 및 저의 역할 (My Role & Core Design)

저는 이 프로젝트의 **백엔드 시스템 전체를 A-Z까지 설계하고 개발**했습니다. 단순히 기능을 구현하는 것을 넘어, **안정성, 효율성, 보안**을 고려하며 다음과 같은 기술적 결정을 내렸습니다.

### 1. 데이터베이스 모델링 (Django ORM)
* `User`, `Team`, `Assignment`의 기본 관계 위에, `TeamMembership`라는 **중개 모델**을 설계하여 '팀 가입 상태(status)', '역할(role)' 등 복잡한 M:N 관계를 효과적으로 관리했습니다.
* `Submission`과 `SubmissionFile`을 **1:N 관계**로 분리하여, 여러 개의 파일을 첨부하는 요구사항을 유연하게 해결했습니다.
* `Submission`과 `Grade`를 **1:1 관계**로 설계하여 채점 정보가 제출물에 고유하게 종속되도록 했습니다.

### 2. RESTful API 엔드포인트 설계
* `teams/<team_id>/assignments/<assignment_id>/submit`처럼, URL만 보고도 데이터의 관계와 계층을 파악할 수 있도록 `urls.py`를 **RESTful 원칙**에 따라 설계했습니다.

### 3. 안전한 접근 제어 (보안 및 인가)
* `@login_required` 데코레이터를 사용해 **인증(Authentication)**을 처리했습니다.
* 모든 View 함수 초입에서 `team.owner_id == request.user.id` 또는 `TeamMembership.objects.filter(...)`를 통해, **'로그인한 사용자가 이 팀의 소유자(교수) 혹은 승인된 멤버가 맞는가?'**를 검증하는 **상세 인가(Authorization)** 로직을 구현하고, 권한이 없으면 `HttpResponseForbidden(403)`으로 안전하게 처리했습니다.

### 4. 견고한 비즈니스 로직 설계 (views.py & models.py)
* **데이터 무결성:** `signup` View에서 **`transaction.atomic()`**을 사용, `User`와 `StudentProfile` 생성이 둘 다 성공하거나 실패하도록 하여(All-or-Nothing) 데이터 무결성을 확보했습니다.
* **모델 중심 로직:** `TeamMembership` 모델 내에 `approve()`, `reject()` 같은 메서드를 구현하여, View가 아닌 Model이 비즈니스 로직(상태 변경, 시간 기록)을 갖도록 설계했습니다.
* **스토리지 관리:** `SubmissionFile` 모델의 `delete()` 메서드를 오버라이드(Override)하여, DB 레코드가 삭제될 때 **실제 저장소(media)의 파일까지 함께 삭제**되도록 구현해 '고아 파일(orphaned file)'이 남지 않도록 했습니다.

### 5. 효율적인 DB 처리 및 예외 처리
* `get_object_or_404()`를 적극적으로 활용해, 존재하지 않는 데이터 요청 시 500 에러 대신 404 페이지를 반환하도록 안정적으로 예외 처리를 했습니다.
* `Submission.objects.get_or_create()`를 활용하여, "기존 제출물이 있으면 가져오고, 없으면 생성하라"는 복잡한 로직을 단 한 줄의 쿼리로 최적화했습니다.

## 4. 프로젝트 회고 및 개선 방향 (Lessons Learned)

이 프로젝트를 통해 Django의 핵심 기능인 ORM, View 설계, 인증/인가 로직을 깊이 있게 이해할 수 있었습니다. 특히 `models.py`에서 데이터 관계를 정의하는 것이 전체 애플리케이션의 안정성에 얼마나 중요한지 체감했습니다.

다만, 파일 업로드 로직(`assignment_submit` View)에서 '기존 파일 삭제'와 '새 파일 생성'이 트랜잭션으로 묶여있지 않아, 만약 새 파일 저장 중 에러가 발생하면 기존 파일만 삭제되고 데이터가 꼬일 수 있는 잠재적 위험을 발견했습니다.

**[개선 방향]**
향후 이 로직 전체를 **`django.db.transaction.atomic()`** 블록으로 감쌀 계획입니다. (현재 `signup` View와 `team_delete` View에는 이 방식이 적용되어 있습니다.) 이를 통해 파일 처리의 **데이터 원자성(Atomicity)**을 보장하여 100% 성공하거나, 실패할 경우 100% 롤백(취소)되도록 개선할 것입니다.

## 5. 로컬에서 실행하기 (Getting Started)

### 1. 프로젝트 복제
```bash
git clone [https://github.com/chakihwan/kp-submit.git](https://github.com/chakihwan/kp-submit.git)
cd kp-submit

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

## 💡 향후 추가 기능 계획 (Future Work)

- [ ] **실시간 알림 기능**: 과제 마감 임박, 채점 완료, 새 과제 등록 시 사용자에게 알림 전송
- [ ] **대시보드 기능**: 미제출 과제, 마감 임박 과제 등 주요 정보를 요약해서 보여주는 페이지
- [ ] **파일 미리보기**: 제출된 PDF, 이미지, 소스코드 등을 웹에서 바로 확인할 수 있는 기능
- [ ] **전체 관리자 페이지**: 시스템의 모든 팀, 사용자, 과제 현황을 모니터링하는 슈퍼유저용 페이지
