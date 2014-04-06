python3.2 setup.py bdist_dmg
cp templates/template.html templates/template_temp.html
cp templates/template_chancecoin.com.html templates/template.html
cp templates/index.html templates/index_temp.html
cp templates/index_chancecoin.com.html templates/index.html
cp templates/wallet.html templates/wallet_temp.html
cp templates/wallet_chancecoin.com.html templates/wallet.html
cp templates/casino.html templates/casino_temp.html
cp templates/casino_chancecoin.com.html templates/casino.html
cp templates/balances.html templates/balances_temp.html
cp templates/balances_chancecoin.com.html templates/balances.html
python3.2 server.py &
sleep 5
rm -Rf chancecoin.com
mkdir chancecoin.com
cp -r static chancecoin.com/
cp .htaccess chancecoin.com/
mkdir chancecoin.com/static/downloads
cp build/*.dmg chancecoin.com/static/downloads
cp build/*.zip chancecoin.com/static/downloads
wget -O chancecoin.com/index.html http://0.0.0.0:8080/
wget -O chancecoin.com/participate.html http://0.0.0.0:8080/participate
wget -O chancecoin.com/technical.html http://0.0.0.0:8080/technical
wget -O chancecoin.com/freebies.html http://0.0.0.0:8080/freebies
wget -O chancecoin.com/casino.html http://0.0.0.0:8080/casino
wget -O chancecoin.com/wallet.html http://0.0.0.0:8080/wallet
wget -O chancecoin.com/balances.html http://0.0.0.0:8080/balances
killall -9 Python
mv templates/template_temp.html templates/template.html
mv templates/index_temp.html templates/index.html
mv templates/wallet_temp.html templates/wallet.html
mv templates/casino_temp.html templates/casino.html
mv templates/balances_temp.html templates/balances.html
