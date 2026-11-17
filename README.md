# 글 쓰는 블로그

작은배가 소개하는 블로그의 최신 글 50개를 모읍니다. Python 3.11 이상과 curl이 있는 환경에서 `python3 build.py`를 실행하면 public 디렉터리에 정적 HTML과 CSS를 생성합니다. 홈의 ‘작성자별로 보기’에서 각 작성자 페이지로 이동합니다.

피드 주소는 feeds.json에서 관리합니다. snapshot.json은 최초 배포용 수집본이며 이후 GitHub Actions는 매시간 17분에 갱신을 예약하고 최근 수집본을 캐시에 보관합니다. 피드 요청이 실패하면 해당 블로그의 이전 글을 유지합니다. 전체 요청 실패 시 배포를 중단합니다.

배포 대상은 GitHub Pages이며 소스는 GitHub Actions, 사용자 도메인은 blogs.jagunbae.com입니다.
