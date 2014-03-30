<?php
header('Access-Control-Allow-Origin: *');
header('Content-Type: text/html');
$url = "https://blockchain.info/charts/balance?showDataPoints=false&timespan=&show_header=true&daysAverageString=1&scale=0&format=json&address=1ChancecoinXXXXXXXXXXXXXXXXXZELUFD";
$json = file_get_contents($url);
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
