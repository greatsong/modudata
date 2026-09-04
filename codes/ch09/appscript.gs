// 9장 접수창구 - 구글 시트에 딸린 Apps Script (시트 메뉴 [확장 프로그램] → [Apps Script])
// 배포: [배포] → [새 배포] → 유형 '웹 앱', 실행 '나', 액세스 권한 '모든 사용자'
function doGet(e) {
  const sh = SpreadsheetApp.getActiveSheet();
  if (e.parameter.member) {                    // 값이 붙어 오면 → 시트에 저장
    const now = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
    sh.appendRow(["'" + now, e.parameter.member, e.parameter.menu, e.parameter.type]);  // 작은따옴표 = 시트가 날짜로 바꾸지 못하게 문자 그대로
    return ContentService.createTextOutput("OK");
  }
  const rows = sh.getDataRange().getValues();  // 안 붙어 오면 → 전체 기록 돌려주기
  return ContentService.createTextOutput(JSON.stringify(rows))
                       .setMimeType(ContentService.MimeType.JSON);
}
