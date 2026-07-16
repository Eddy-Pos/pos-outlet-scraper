function triggerScraper() {
  var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');

  var url = 'https://api.github.com/repos/Eddy-Pos/pos-outlet-scraper/actions/workflows/scrape.yml/dispatches';

  var options = {
    method: 'post',
    headers: {
      'Authorization': 'Bearer ' + token,
      'Accept': 'application/vnd.github+json'
    },
    contentType: 'application/json',
    payload: JSON.stringify({ ref: 'main' }),
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(url, options);
    var code = response.getResponseCode();
    Logger.log('Status: ' + code + ' | ' + response.getContentText());
  } catch (e) {
    Logger.log('Error: ' + e.toString());
  }
}
