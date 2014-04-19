<?php
error_reporting(0);
header('Access-Control-Allow-Origin: *');
header('Content-Type: text/html');
//$url = "https://blockchain.info/charts/balance?showDataPoints=false&timespan=&show_header=true&daysAverageString=1&scale=0&format=json&address=1ChancecoinXXXXXXXXXXXXXXXXXZELUFD";
$url = "http://chancecoin.com/static/chart-data.json";
$json = file_get_contents($url);

/*
$save_path = 'download/';
$ch = curl_init($url);
curl_setopt($ch,CURLOPT_USERAGENT,'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13');
$json = curl_exec($ch);
curl_close($ch);
*/

$json = json_decode($json, true);
for ($i=0; $i<count($json['values']); $i++) {
  $value = $json['values'][$i];
  print $value['x'];
  print ",";
  print $value['y'];
  if ($i<count($json['values'])-1) {
    print ";";
  }
}
?>
