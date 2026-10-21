// 모두의 점심 - 구글 시트에 딸린 연결 프로그램 (시트 메뉴 [확장 프로그램] → [Apps Script])
// 아래 여기에_시트_ID만 자신의 시트 ID로 바꾸세요.
// 시트 주소에서 /d/ 와 그다음 / 사이에 있는 긴 문자열입니다.
const SPREADSHEET_ID = "여기에_시트_ID";
const SHEET_NAME = "votes";

function sheet_() {
  return SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
}

// 기록을 요청하면 시트의 내용을 돌려준다.
// 첫 줄은 머리글(시각, 팀원, 메뉴, 구분)이고 그 아래가 기록이다.
function doGet(e) {
  const rows = sheet_().getDataRange().getValues();
  return ContentService.createTextOutput(JSON.stringify(rows))
                       .setMimeType(ContentService.MimeType.JSON);
}

// 앱이 투표를 보내면 시트에 한 줄을 쓴다.
// 받는 형태 세 가지를 모두 허용한다.
//   ① JSON 본문 {"data": {"member": "민지", "menu": "제육볶음", "type": "희망메뉴"}}
//   ② JSON 본문 {"member": "민지", "menu": "제육볶음", "type": "희망메뉴"}
//   ③ 폼 방식(member=민지&menu=제육볶음&type=희망메뉴)
// 시각은 앱이 아니라 이 프로그램이 한국 시간으로 적는다.
function doPost(e) {
  try {
    let data = {};
    if (e.postData && e.postData.contents) {
      try {
        const body = JSON.parse(e.postData.contents);
        data = body.data || body;
      } catch (err) {
        data = e.parameter || {};
      }
    } else {
      data = e.parameter || {};
    }
    const member = String(data.member || "").trim();
    const menu = String(data.menu || "").trim();
    const type = String(data.type || "").trim();
    if (!member || !menu || !type) {
      return json_({ ok: false, error: "member, menu, type이 모두 필요합니다" });
    }
    // 여러 사람이 동시에 보내도 한 줄씩 차례대로 쓰도록 잠근다.
    // 잠그지 않으면 다른 요청이 사이에 줄을 더해 엉뚱한 줄의 시각을 고칠 수 있다.
    const lock = LockService.getScriptLock();
    lock.waitLock(10000);   // 최대 10초 기다린다. 그래도 차례가 오지 않으면 오류로 알린다
    try {
      const now = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
      const sh = sheet_();
      sh.appendRow([now, member, menu, type]);
      // 시각 칸을 문자로 고정한다. 시트가 날짜로 바꾸면 앱이 읽을 때 형식이 달라진다.
      const last = sh.getLastRow();
      sh.getRange(last, 1).setNumberFormat("@").setValue(now);
      SpreadsheetApp.flush();   // 잠금을 풀기 전에 시트에 반영한다
    } finally {
      lock.releaseLock();
    }
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
                       .setMimeType(ContentService.MimeType.JSON);
}
